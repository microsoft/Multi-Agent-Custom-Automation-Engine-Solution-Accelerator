"""
Workspace HTTP layer — thin adapter over v4.common.services.workspace_service.

This module owns ONLY the HTTP concerns: EasyAuth identity extraction,
request/response models, and route wiring. Every filesystem/git primitive
(workspace_for, _resolve, _git, _contained, origins, metadata) lives in the
shared workspace_service so the agent lanes call the SAME functions with the
user_id they already carry — one resolver, never a parallel file world.

    frontend (Monaco)  ──►  /workspace/{workspace_id}/...   ─┐
    MCP filesystem / agents (service import, no HTTP)       ─┼──►  workspace_service
    git (init / commit / log / restore)  ◄───────────────────┘

Endpoints (all authenticated; user_id comes from EasyAuth headers)
------------------------------------------------------------------
GET  /workspace/{ws}/files            → flat list (dropdown feed; capped)
GET  /workspace/{ws}/entries?path=    → ONE directory level (lazy explorer)
GET  /workspace/{ws}/files/{path}     → { path, content, size, mtime }
PUT  /workspace/{ws}/files/{path}     → write (creates parent dirs inside ws)
GET  /workspace/{ws}/diff/{path}      → git HEAD vs disk for Monaco DiffEditor
POST /workspace/{ws}/commit           → git add -A && commit → { sha }
GET  /workspace/{ws}/log              → last 50 commits
POST /workspace/{ws}/restore/{path}   → git checkout {ref} -- path
GET/POST/DELETE /workspaces           → named-workspace management
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from auth.auth_utils import get_authenticated_user_details
from v4.common.services.workspace_service import (
    _GIT_IDENTITY,
    _META_FILE,
    _SAFE_ID,
    _SAFE_REF,
    MAX_FILE_BYTES,
    MAX_LIST_ENTRIES,
    WORKSPACE_ROOT,
    _clone_into,
    _contained,
    _count_files,
    _git,
    _init_lock,
    _link_into,
    _read_meta,
    _read_text_guarded,
    _resolve,
    _write_meta,
    user_root_for,
    workspace_for,
)

logger = logging.getLogger(__name__)

#: Intentos de borrado tras apartar el árbol. El ENOTEMPTY de SMB es un listado
#: rancio, no un directorio realmente ocupado: un segundo barrido lo limpia.
_RMTREE_ATTEMPTS = 3

# Router for per-workspace file operations  (/workspace/{workspace_id}/…)
workspace_router = APIRouter(prefix="/workspace/{workspace_id}", tags=["workspace"])
# Router for workspace management  (/workspaces  and  /workspaces/{workspace_id})
workspaces_router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# ── HTTP identity extraction (the ONLY thing this layer adds) ────────────────


def _auth_user(request: Request) -> str:
    try:
        details = get_authenticated_user_details(request_headers=request.headers)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    user_id = details.get("user_principal_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="no user found")
    return str(user_id)


def _workspace_for(request: Request, workspace_id: str) -> Path:
    """HTTP wrapper: extract the EasyAuth principal, delegate to the service.

    ``create=False``: una petición HTTP nunca hace nacer un workspace. Crearlo
    desde una lectura resucitaba el que el usuario acababa de borrar (el
    frontend sigue consultando el seleccionado) y el ``create`` siguiente
    tomaba ese ``.git`` como prueba de existencia, así que no clonaba nada.
    Nacer es asunto de ``POST /workspaces`` y del carril de agente."""
    return workspace_for(_auth_user(request), workspace_id, create=False)


def _user_root(request: Request) -> Path:
    return user_root_for(_auth_user(request))


# ── models ───────────────────────────────────────────────────────────────────


class FileInfo(BaseModel):
    path: str
    size: int
    mtime: float


class FileListResponse(BaseModel):
    workspace_id: str
    files: list[FileInfo]
    truncated: bool


class DirEntry(BaseModel):
    name: str
    type: str  # "directory" | "file"
    size: int | None = None  # files only
    status: str | None = None  # "M" modified · "?" untracked · None clean


class EntriesResponse(BaseModel):
    workspace_id: str
    path: str  # workspace-relative dir ("" = root)
    entries: list[DirEntry]
    truncated: bool


class FileResponse(BaseModel):
    path: str
    content: str
    size: int
    mtime: float


class FilePutRequest(BaseModel):
    content: str


class FilePutResponse(BaseModel):
    path: str
    size: int
    mtime: float


class DiffResponse(BaseModel):
    path: str
    original: str  # git HEAD (empty string if untracked)
    modified: str  # current disk content


class CommitRequest(BaseModel):
    message: str = "Update workspace"


class CommitResponse(BaseModel):
    committed: bool
    sha: str
    message: str


class LogEntry(BaseModel):
    sha: str
    author: str
    date: str
    message: str


class LogResponse(BaseModel):
    workspace_id: str
    commits: list[LogEntry]


class RestoreRequest(BaseModel):
    ref: str = "HEAD"


# ── endpoints ────────────────────────────────────────────────────────────────


@workspace_router.get("/files", response_model=FileListResponse)
def list_files(request: Request, workspace_id: str) -> FileListResponse:
    """List every file in the workspace (excluding .git)."""
    ws = _workspace_for(request, workspace_id)
    files: list[FileInfo] = []
    truncated = False
    for root, dirs, names in os.walk(ws):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in sorted(names):
            if name == _META_FILE:
                continue
            full = Path(root) / name
            stat = full.stat()
            files.append(
                FileInfo(
                    path=str(full.relative_to(ws)),
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                )
            )
            if len(files) >= MAX_LIST_ENTRIES:
                truncated = True
                break
        if truncated:
            break
    files.sort(key=lambda f: f.path)
    return FileListResponse(workspace_id=workspace_id, files=files, truncated=truncated)


@workspace_router.get("/entries", response_model=EntriesResponse)
def list_entries(
    request: Request, workspace_id: str, path: str = ""
) -> EntriesResponse:
    """ONE directory level, on demand — the lazy project-explorer contract.
    The limit is per directory, never "the first N files of the whole repo".
    Git markers: files carry their own state; a directory carries "M"/"?" when
    anything beneath it changed (VS Code-style aggregate)."""
    ws = _workspace_for(request, workspace_id)
    raw_rel = path.strip().strip("/")
    base = _resolve(ws, raw_rel) if raw_rel else ws
    if not base.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory.")
    # Contained value only from here on (never the raw query string).
    rel = str(base.relative_to(ws)) if raw_rel else ""

    child_status: dict[str, str] = {}
    try:
        porcelain = _git(
            ws, "status", "--porcelain", "--untracked-files=all", "--", rel or "."
        )
    except HTTPException as exc:
        if exc.status_code not in {503, 504}:
            raise
        porcelain = None

    if porcelain and porcelain.returncode == 0:
        prefix = f"{rel}/" if rel else ""
        for line in porcelain.stdout.decode("utf-8", errors="replace").splitlines():
            if len(line) < 4:
                continue
            code, p = line[:2], line[3:].strip().strip('"')
            if prefix and not p.startswith(prefix):
                continue
            child = p[len(prefix) :].split("/", 1)[0]
            mark = "?" if code == "??" else "M"
            # Any tracked change under a child wins over pure-untracked.
            if child_status.get(child) != "M":
                child_status[child] = mark
    entries: list[DirEntry] = []
    truncated = False
    dirs: list[DirEntry] = []
    files_e: list[DirEntry] = []
    for entry in sorted(base.iterdir(), key=lambda e: e.name.lower()):
        if entry.name == ".git" or entry.name == _META_FILE:
            continue
        if len(dirs) + len(files_e) >= MAX_LIST_ENTRIES:
            truncated = True
            break
        if entry.is_dir():
            dirs.append(
                DirEntry(
                    name=entry.name,
                    type="directory",
                    status=child_status.get(entry.name),
                )
            )
        else:
            files_e.append(
                DirEntry(
                    name=entry.name,
                    type="file",
                    size=entry.stat().st_size,
                    status=child_status.get(entry.name),
                )
            )
    entries = dirs + files_e  # directories first, like any real explorer
    return EntriesResponse(
        workspace_id=workspace_id, path=rel, entries=entries, truncated=truncated
    )


class SearchResponse(BaseModel):
    workspace_id: str
    query: str
    matches: list[str]  # workspace-relative paths
    truncated: bool


@workspace_router.get("/search", response_model=SearchResponse)
def search_files(request: Request, workspace_id: str, q: str = "") -> SearchResponse:
    """Find files by name across the WHOLE workspace — git as the index
    (`ls-files` tracked + others), never an os.walk. Case-insensitive
    substring on the relative path; capped at 200 matches."""
    ws = _workspace_for(request, workspace_id)
    query = q.strip().lower()
    if not query:
        return SearchResponse(
            workspace_id=workspace_id, query=q, matches=[], truncated=False
        )
    names: set[str] = set()
    for extra in ((), ("--others", "--exclude-standard")):
        result = _git(ws, "ls-files", *extra)
        if result.returncode == 0:
            names.update(result.stdout.decode("utf-8", errors="replace").splitlines())
    names.discard(_META_FILE)
    matches = sorted(p for p in names if query in p.lower())
    return SearchResponse(
        workspace_id=workspace_id,
        query=q,
        matches=matches[:200],
        truncated=len(matches) > 200,
    )


@workspace_router.get("/files/{path:path}", response_model=FileResponse)
def get_file(request: Request, workspace_id: str, path: str) -> FileResponse:
    """Read a workspace file as text."""
    ws = _workspace_for(request, workspace_id)
    resolved = _resolve(ws, path)
    raw = _read_text_guarded(resolved, path)
    stat = resolved.stat()
    return FileResponse(
        path=path,
        content=raw.decode("utf-8", errors="replace"),
        size=stat.st_size,
        mtime=stat.st_mtime,
    )


@workspace_router.put("/files/{path:path}", response_model=FilePutResponse)
def put_file(
    request: Request, workspace_id: str, path: str, body: FilePutRequest
) -> FilePutResponse:
    """Write a workspace file (parent directories are created inside the ws)."""
    ws = _workspace_for(request, workspace_id)
    resolved = _resolve(ws, path)
    if resolved.exists() and not resolved.is_file():
        raise HTTPException(status_code=400, detail="Path is a directory.")
    encoded = body.content.encode("utf-8")
    if len(encoded) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Content exceeds {MAX_FILE_BYTES // 1024} KB limit.",
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_bytes(encoded)
    stat = resolved.stat()
    return FilePutResponse(path=path, size=stat.st_size, mtime=stat.st_mtime)


@workspace_router.get("/diff/{path:path}", response_model=DiffResponse)
def get_diff(request: Request, workspace_id: str, path: str) -> DiffResponse:
    """Return git HEAD vs disk for Monaco DiffEditor."""
    ws = _workspace_for(request, workspace_id)
    resolved = _resolve(ws, path)
    raw = _read_text_guarded(resolved, path)
    rel = str(resolved.relative_to(ws))
    show = _git(ws, "show", f"HEAD:{rel}")
    head_content = (
        show.stdout.decode("utf-8", errors="replace") if show.returncode == 0 else ""
    )
    return DiffResponse(
        path=path,
        original=head_content,
        modified=raw.decode("utf-8", errors="replace"),
    )


# ── diagnostics (Python) ─────────────────────────────────────────────────────
#
# Monaco ships language workers for TS/JS/JSON/CSS/HTML but has NO Python
# analysis. The editor posts the in-memory buffer here (debounced) and gets
# back LSP-shaped diagnostics it turns into markers (red squiggles + hover,
# Problems-style). Deterministic cascade, best available first:
#   1. ruff  — syntax + pyflakes rules (F821 undefined name, F401 unused
#              import, E1xx indentation, …), JSON output, ~50 ms.
#   2. compile() in-process — syntax / IndentationError only, always available.
# The file on disk is never touched: the buffer is passed via stdin so
# unsaved edits are diagnosed live, like VS Code.


class DiagnosticsRequest(BaseModel):
    path: str
    content: str
    language: str = "python"


class Diagnostic(BaseModel):
    line: int  # 1-based
    column: int  # 1-based
    end_line: int | None = None
    end_column: int | None = None
    severity: str  # error | warning | info | hint
    message: str
    code: str | None = None
    source: str | None = None


class DiagnosticsResponse(BaseModel):
    path: str
    engine: str  # ruff | compile | none
    diagnostics: list[Diagnostic]


_RUFF_BIN = shutil.which("ruff")
# Rules Monaco can show as markers meaningfully. Pyflakes (F) + pycodestyle
# errors (E) + warnings (W) + bugbear-ish pyupgrade left out on purpose: this is
# a live editor, not CI — noise kills the signal.
_RUFF_SELECT = "F,E1,E9,W6"


def _ruff_diagnostics(path: str, content: str) -> list[Diagnostic] | None:
    if not _RUFF_BIN:
        return None
    import json
    import subprocess

    try:
        proc = subprocess.run(
            [
                _RUFF_BIN,
                "check",
                "--select",
                _RUFF_SELECT,
                "--output-format",
                "json",
                "--no-cache",
                "--isolated",
                "--stdin-filename",
                path,
                "-",
            ],
            input=content.encode("utf-8"),
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    try:
        items = json.loads(proc.stdout.decode("utf-8", errors="replace") or "[]")
    except ValueError:
        return None
    out: list[Diagnostic] = []
    for it in items:
        loc = it.get("location") or {}
        end = it.get("end_location") or {}
        code = it.get("code") or ""
        # Syntax errors (ruff ≥0.15 reports code="invalid-syntax"; older: null)
        # and undefined names are errors; the rest are warnings.
        is_error = code in ("", "invalid-syntax") or code.startswith(
            ("E9", "F821", "F822", "F823")
        )
        out.append(
            Diagnostic(
                line=int(loc.get("row", 1)),
                column=int(loc.get("column", 1)),
                end_line=int(end.get("row", loc.get("row", 1))),
                end_column=int(end.get("column", loc.get("column", 1))),
                severity="error" if is_error else "warning",
                message=str(it.get("message", "")),
                code=code or None,
                source="ruff",
            )
        )
    return out


def _compile_diagnostics(path: str, content: str) -> list[Diagnostic]:
    try:
        compile(content, path, "exec")
    except SyntaxError as exc:  # includes IndentationError / TabError
        line = exc.lineno or 1
        col = exc.offset or 1
        end_line = getattr(exc, "end_lineno", None) or line
        # IndentationError may report end_offset=-1; clamp to a 1-char range.
        end_col = max(getattr(exc, "end_offset", None) or 0, col + 1)
        return [
            Diagnostic(
                line=line,
                column=col,
                end_line=end_line,
                end_column=end_col,
                severity="error",
                message=f"{type(exc).__name__}: {exc.msg}",
                code=type(exc).__name__,
                source="python",
            )
        ]
    return []


@workspace_router.post("/diagnostics", response_model=DiagnosticsResponse)
def diagnostics(
    request: Request, workspace_id: str, body: DiagnosticsRequest
) -> DiagnosticsResponse:
    """Live diagnostics for the editor buffer (unsaved content, never disk)."""
    _workspace_for(request, workspace_id)  # auth + containment, same as the rest
    if body.language != "python":
        return DiagnosticsResponse(path=body.path, engine="none", diagnostics=[])
    if len(body.content.encode("utf-8")) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Content too large.")
    result = _ruff_diagnostics(body.path, body.content)
    if result is not None:
        return DiagnosticsResponse(path=body.path, engine="ruff", diagnostics=result)
    return DiagnosticsResponse(
        path=body.path,
        engine="compile",
        diagnostics=_compile_diagnostics(body.path, body.content),
    )


@workspace_router.post("/commit", response_model=CommitResponse)
def commit(request: Request, workspace_id: str, body: CommitRequest) -> CommitResponse:
    """Stage everything and commit; no-op (committed=false) when clean."""
    ws = _workspace_for(request, workspace_id)
    add = _git(ws, "add", "-A")
    if add.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="git add failed: " + add.stderr.decode("utf-8", errors="replace"),
        )
    head_res = _git(ws, "rev-parse", "HEAD")
    if head_res.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="git rev-parse failed: "
            + head_res.stderr.decode("utf-8", errors="replace"),
        )
    head = head_res.stdout.decode("utf-8", errors="replace").strip()

    staged = _git(ws, "diff", "--cached", "--quiet")
    if staged.returncode == 0:
        return CommitResponse(committed=False, sha=head, message="")
    if staged.returncode != 1:
        raise HTTPException(
            status_code=500,
            detail="git diff --cached failed: "
            + staged.stderr.decode("utf-8", errors="replace"),
        )
    message = body.message.strip() or "Update workspace"
    result = _git(ws, "commit", "-q", "-m", message)
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="git commit failed: "
            + result.stderr.decode("utf-8", errors="replace"),
        )
    sha = _git(ws, "rev-parse", "HEAD").stdout.decode().strip()
    return CommitResponse(committed=True, sha=sha, message=message)


@workspace_router.get("/log", response_model=LogResponse)
def log(request: Request, workspace_id: str) -> LogResponse:
    """Last 50 commits of this workspace."""
    ws = _workspace_for(request, workspace_id)
    result = _git(ws, "log", "-n", "50", "--pretty=format:%H%x1f%an%x1f%aI%x1f%s")
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="git log failed: " + result.stderr.decode("utf-8", errors="replace"),
        )
    commits: list[LogEntry] = []
    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            commits.append(
                LogEntry(sha=parts[0], author=parts[1], date=parts[2], message=parts[3])
            )
    return LogResponse(workspace_id=workspace_id, commits=commits)


@workspace_router.post("/restore/{path:path}", response_model=FileResponse)
def restore(
    request: Request, workspace_id: str, path: str, body: RestoreRequest
) -> FileResponse:
    """Restore one file from a ref (default HEAD) and return its content."""
    ws = _workspace_for(request, workspace_id)
    resolved = _resolve(ws, path)
    ref = body.ref.strip() or "HEAD"
    if not _SAFE_REF.match(ref):
        raise HTTPException(status_code=400, detail="Invalid git ref.")
    rel = str(resolved.relative_to(ws))
    result = _git(ws, "checkout", "-q", ref, "--", rel)
    if result.returncode != 0:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot restore {path} from {ref}: "
            + result.stderr.decode("utf-8", errors="replace"),
        )
    raw = _read_text_guarded(resolved, path)
    stat = resolved.stat()
    return FileResponse(
        path=path,
        content=raw.decode("utf-8", errors="replace"),
        size=stat.st_size,
        mtime=stat.st_mtime,
    )


# ── workspace management endpoints (/workspaces) ─────────────────────────────


class WorkspaceSummary(BaseModel):
    workspace_id: str
    name: str
    created_at: str  # ISO-8601
    file_count: int
    #: Rama actual del workspace: lo que el usuario necesita ver para saber
    #: contra qué trabaja, sin leer logs. Vacío si no es un repo con ramas.
    branch: str = ""
    #: Este workspace es el registro de incidentes: contiene docs/incidents.
    #: Cuando además es el propio del reconciliador, él lo mantiene al día.
    is_incident_registry: bool = False
    reconciler_owned: bool = False


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceSummary]


class WorkspaceCreateRequest(BaseModel):
    name: str
    workspace_id: str | None = None  # client-supplied slug; server generates if omitted
    # Where the workspace is born from (both optional; empty init otherwise):
    repo_url: str | None = None  # https git clone — works identically in prod
    # Rama declarada al montar: parte del contrato del workspace (clon durable,
    # sandbox y fast-forward del registro la conservan). Sin ella, la rama por
    # defecto del remoto, y la resuelta queda igualmente registrada en el meta.
    branch: str | None = None
    repo_token: str | None = None  # transient clone auth; NEVER stored anywhere
    local_path: str | None = None  # link an existing local folder (dev only)


def _reconciler_owned_path() -> Path | None:
    """Resolved physical path of the workspace the reconciler keeps current, or
    ``None``. Quién se adelanta solo lo decide el descubrimiento por contenido,
    no el nombre del workspace: comparar contra ``incident-registry`` decía "no"
    en el registro que el reconciliador SÍ mantiene, porque un usuario crea el
    workspace con un nombre y una URL y nunca lo bautiza así. Se compara la ruta
    física para que un alias del mismo clon no cuente como otro."""
    from v4.control.workspace_capability import discover

    registry = discover()
    return (
        workspace_for(registry.user_id, registry.workspace_id).resolve()
        if registry is not None
        else None
    )


def _workspace_summary(entry: Path, kept_current: Path | None) -> WorkspaceSummary:
    """Build the summary a workspace exposes, identical for create and list, so
    the frontend sees the same shape no matter which endpoint produced it. La
    rama se lee EN VIVO del HEAD (no del meta), para que el selector muestre
    contra qué rama trabaja el usuario sin una segunda consulta ni poder
    divergir del disco."""
    meta = _read_meta(entry)
    head = _git(entry, "symbolic-ref", "--short", "HEAD")
    return WorkspaceSummary(
        workspace_id=entry.name,
        name=meta.get("name", entry.name),
        branch=(
            head.stdout.decode("utf-8", errors="replace").strip()
            if head.returncode == 0
            else ""
        ),
        is_incident_registry=any((entry / "docs/incidents").glob("*.json")),
        reconciler_owned=kept_current is not None and entry.resolve() == kept_current,
        created_at=meta.get(
            "created_at",
            datetime.fromtimestamp(entry.stat().st_ctime, tz=UTC).isoformat(),
        ),
        file_count=_count_files(entry),
    )


@workspaces_router.get("", response_model=WorkspaceListResponse)
def list_workspaces(request: Request) -> WorkspaceListResponse:
    """List all workspaces owned by the authenticated user."""
    user_root = _user_root(request)
    results: list[WorkspaceSummary] = []
    if not user_root.exists():
        return WorkspaceListResponse(workspaces=[])
    kept_current = _reconciler_owned_path()
    for entry in sorted(user_root.iterdir()):
        if not entry.is_dir() or not (entry / ".git").is_dir():
            continue
        # Only NAMED workspaces (created via create_workspace, which writes the
        # meta file) belong in the selector; auto-created per-session spaces
        # are reachable through the session fallback, never listed here.
        if not (entry / _META_FILE).exists():
            continue
        results.append(_workspace_summary(entry, kept_current))
    return WorkspaceListResponse(workspaces=results)


@workspaces_router.post("", response_model=WorkspaceSummary, status_code=201)
def create_workspace(
    request: Request, body: WorkspaceCreateRequest
) -> WorkspaceSummary:
    """Create (or re-open) a named workspace."""
    user_id = _auth_user(request)
    if not _SAFE_ID.match(user_id):
        raise HTTPException(status_code=400, detail="Invalid user id.")

    # Derive workspace_id from supplied name if not given
    raw_id = (body.workspace_id or body.name).strip()
    # Slugify: lowercase, replace non-alnum runs with '-', trim dashes
    slug = re.sub(r"[^A-Za-z0-9]+", "-", raw_id.lower()).strip("-")
    if not slug:
        slug = "workspace"
    workspace_id = slug[:64]

    if not _SAFE_ID.match(workspace_id):
        raise HTTPException(status_code=400, detail="Invalid workspace id.")

    ws = _contained(WORKSPACE_ROOT, user_id, workspace_id)
    now_iso = datetime.now(tz=UTC).isoformat()

    if not (ws / ".git").is_dir():
        with _init_lock:
            if not (ws / ".git").is_dir():
                linked_target: Path | None = None
                if body.local_path:
                    linked_target = _link_into(ws, body.local_path)
                elif body.repo_url:
                    _clone_into(ws, body.repo_url.strip(), body.repo_token, body.branch)
                else:
                    ws.mkdir(parents=True, exist_ok=True)
                    # Empty-born workspace: the meta exclusion is OURS to commit
                    # (idempotent: never clobber a .gitignore that already exists)
                    gitignore = ws / ".gitignore"
                    existing = (
                        gitignore.read_text(encoding="utf-8")
                        if gitignore.exists()
                        else ""
                    )
                    if _META_FILE not in existing.splitlines():
                        prefix = existing.rstrip("\n") + "\n" if existing else ""
                        gitignore.write_text(
                            prefix + _META_FILE + "\n", encoding="utf-8"
                        )
                    for cmd in (
                        ("init", "-q"),
                        ("config", "user.name", _GIT_IDENTITY[0]),
                        ("config", "user.email", _GIT_IDENTITY[1]),
                        ("commit", "--allow-empty", "-q", "-m", "init workspace"),
                    ):
                        result = _git(ws, *cmd)
                        if result.returncode != 0:
                            raise HTTPException(
                                status_code=500,
                                detail="Workspace git init failed: "
                                + result.stderr.decode("utf-8", errors="replace"),
                            )
                meta = {"name": body.name.strip(), "created_at": now_iso}
                if body.repo_url:
                    meta["repo_url"] = body.repo_url.strip()
                # La rama RESUELTA (la declarada, o la por defecto del remoto)
                # queda en el meta: es la única fuente durable de esa intención
                # y de ella parten el sandbox del MCP y el registro de INC.
                head = _git(ws, "symbolic-ref", "--short", "HEAD")
                if head.returncode == 0:
                    meta["branch"] = head.stdout.decode(
                        "utf-8", errors="replace"
                    ).strip()
                if linked_target is not None:
                    meta["linked_path"] = str(linked_target)
                _write_meta(ws, meta)
    else:
        # Update name if workspace already exists
        meta = _read_meta(ws)
        meta["name"] = body.name.strip()
        _write_meta(ws, meta)
        now_iso = meta.get("created_at", now_iso)

    # Mismo summary que la lista, vía el mismo builder: la rama se lee EN VIVO
    # del HEAD y ``reconciler_owned`` del descubrimiento por contenido, para que
    # la respuesta del POST que el frontend inserta en estado no diverja del GET
    # siguiente cuando este clon es el único registro de incidentes.
    return _workspace_summary(ws, _reconciler_owned_path())


@workspaces_router.delete(
    "/{workspace_id}",
    status_code=204,
    response_model=None,
    response_class=Response,
)
def delete_workspace(request: Request, workspace_id: str) -> None:
    """Delete a workspace. Linked workspaces are only DETACHED — the real
    project folder is never touched. Everything else is irreversible."""
    user_id = _auth_user(request)
    if not _SAFE_ID.match(user_id):
        raise HTTPException(status_code=400, detail="Invalid user id.")
    if not _SAFE_ID.match(workspace_id):
        raise HTTPException(status_code=400, detail="Invalid workspace id.")
    safe_workspace_id = workspace_id
    ws = _contained(WORKSPACE_ROOT, user_id, safe_workspace_id)
    if ws.is_symlink():
        ws.unlink()  # detach the link; the target project stays intact
        return None
    if not ws.exists():
        raise HTTPException(status_code=404, detail="Workspace not found.")
    # Azure Files (SMB) hace fallar ``rmtree`` a mitad con
    # ``OSError: [Errno 39] Directory not empty`` porque el directorio sigue
    # listando entradas ya desvinculadas (medido en prod sobre un árbol con
    # node_modules). Si eso pasa bajo el NOMBRE REAL queda un cadáver con
    # ``.git``, y el ``create`` siguiente lo re-abre en vez de clonar. Apartarlo
    # con un rename sí es atómico: el nombre queda libre en un solo paso y el
    # borrado lento ya no puede dejar basura donde el usuario la vuelva a pisar.
    # El prefijo con punto no es un workspace_id válido (``_SAFE_ID`` exige
    # empezar con alfanumérico), así que un resto no se confunde con uno real.
    doomed = ws.parent / f".deleting-{safe_workspace_id}-{uuid4().hex[:8]}"
    if doomed.parent != ws.parent:
        raise HTTPException(status_code=400, detail="Invalid workspace path.")
    ws.rename(doomed)
    base_parent = ws.parent.resolve()
    resolved_doomed = doomed.resolve()
    try:
        doomed_rel = resolved_doomed.relative_to(base_parent)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="Invalid workspace path.") from err
    safe_delete_target = (base_parent / doomed_rel).resolve()
    for _ in range(_RMTREE_ATTEMPTS):
        shutil.rmtree(safe_delete_target, ignore_errors=True)
        if not doomed.exists():
            return None
    # El nombre del usuario ya está libre, así que el borrado ES efectivo para
    # él; lo que queda es basura que hay que poder ver, no tapar.
    logger.warning(
        "Workspace %s apartado como %s pero no se pudo borrar del todo",
        workspace_id,
        doomed.name,
    )
    return None
