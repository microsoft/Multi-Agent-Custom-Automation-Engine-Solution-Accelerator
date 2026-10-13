"""
WorkspaceService — the single file substrate shared by every consumer.

    HTTP endpoints (v4/api/workspace_router)  ─┐
    Agent tools (Router/Responses lane)        ─┼──►  workspace_for(user_id, ws_id)
    Plan lane (orchestration file drops)       ─┘     {WORKSPACE_ROOT}/{user_id}/{workspace_id}/

This module is IDENTITY-AGNOSTIC: callers pass an already-authenticated
user_id. The HTTP layer extracts it from EasyAuth headers; the agent lanes
pass the user_id they carry from the chat request. One resolver, N consumers —
never a parallel file world per lane.

Error contract: functions raise fastapi.HTTPException with meaningful status
codes. HTTP callers let them propagate; non-HTTP callers (agent tools) catch
HTTPException and surface `detail` as the tool error string.

Security invariants (do not "simplify" away):
- _contained / the link guards use os.path.normpath + a SIMPLE
  `startswith(base + os.sep)` check — the only form CodeQL recognizes as a
  py/path-injection barrier (compound conditions break recognition; proven
  empirically twice in this repo's PR cycles).
- _resolve then collapses symlinks and re-verifies containment.
- Linked workspaces resolve only under LINK_ROOT and are dev-only.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import threading
from pathlib import Path

from fastapi import HTTPException

from common.config.app_config import config

# ── constants ────────────────────────────────────────────────────────────────

WORKSPACE_ROOT = Path(
    os.getenv("MACAE_WORKSPACE_ROOT") or str(Path.home() / ".macae" / "workspaces")
).resolve()
MAX_FILE_BYTES = 1 * 1024 * 1024  # 1 MB
_META_FILE = ".macae_workspace_meta.json"
#: Workspace propio del reconciliador (registro de incidentes). Configurable
#: vía INCIDENT_REGISTRY_WORKSPACE_ID (p.ej. en prod apunta al workspace del
#: repo); si no está definida, cae al id por convención. Si existe con este
#: id, él lo mantiene al día; cualquier otro workspace se lee tal cual porque
#: es del usuario o de los agentes.
REGISTRY_WORKSPACE_ID = (
    os.getenv("INCIDENT_REGISTRY_WORKSPACE_ID") or "incident-registry"
)

# Leading alphanumeric forbids dotfiles, "." and ".." outright; no separators.
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,127}$")
# Git refs for restore: leading alphanumeric forbids "-option" injection.
_SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./~^-]{0,63}$")
# Clone sources: https only (no ssh/file/git schemes, no leading dash, no spaces).
_SAFE_REPO_URL = re.compile(r"^https://[A-Za-z0-9][A-Za-z0-9._~:/?#@!$&'()*+,;=%-]*$")
# Linked workspaces may only point INSIDE this root (dev: the projects dir).
LINK_ROOT = Path(os.getenv("MACAE_LINK_ROOT", "/workspaces")).resolve()

_GIT_IDENTITY = ("MACAE Workspace", "workspace@macae.local")
_init_lock = threading.Lock()


# ── core primitives ──────────────────────────────────────────────────────────


def _git(ws: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    # ``safe.directory`` declarado por invocación y acotado a ESTE workspace: el
    # share (Azure Files/SMB) reporta un dueño distinto al uid del proceso y git
    # rechaza el árbol con "detected dubious ownership", de modo que TODA
    # operación de git falla sobre el montaje (medido en prod: git status del
    # clon de /data/workspaces). Va como pre-flight contra el contrato conocido,
    # no como manejo del error, y sin config global ni comodín.
    try:
        return subprocess.run(
            ["git", "-c", f"safe.directory={ws}", *args],
            cwd=ws,
            capture_output=True,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="git is not installed in this image; workspaces need it.",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="git operation timed out.") from exc


def _contained(base: Path, *parts: str) -> Path:
    """Join *parts* under *base* with the normpath + startswith containment
    guard — the sanitizer form CodeQL recognizes as a py/path-injection
    barrier. Callers must pre-validate parts semantically; this is the single
    choke point every request-derived path flows through."""
    joined = os.path.normpath(os.path.join(str(base), *parts))
    if not joined.startswith(str(base) + os.sep):
        raise HTTPException(status_code=400, detail="Path outside workspace.")
    return Path(joined)


def workspace_for(user_id: str, workspace_id: str, *, create: bool = True) -> Path:
    """Resolve (and lazily create) a user's workspace directory.

    Identity is INJECTED: the HTTP layer passes the EasyAuth principal, agent
    lanes pass the user_id they carry from the chat request. Single entry
    point to the physical workspace for every consumer.

    ``create=False`` resuelve sin crear y da 404 si no existe. Es lo que usan
    las LECTURAS HTTP: crear desde un GET resucitaba un workspace recién
    borrado —el frontend sigue consultando el que quedó seleccionado— y dejaba
    un ``.git`` vacío; el ``create_workspace`` siguiente veía ese ``.git``, se
    salteaba el nacimiento, NO clonaba y devolvía 201 con el árbol vacío
    (medido en prod 2026-09-27: reflog con una sola entrada
    ``commit (initial): init workspace`` y ``config`` sin ``remote``). La
    creación diferida sigue viva para los carriles de agente, que la necesitan
    para el workspace por sesión."""
    if not _SAFE_ID.match(user_id):
        raise HTTPException(status_code=400, detail="Invalid user id.")
    if not _SAFE_ID.match(workspace_id):
        raise HTTPException(status_code=400, detail="Invalid workspace id.")
    ws = _contained(WORKSPACE_ROOT, user_id, workspace_id)
    if ws.is_symlink():
        # Linked workspace (dev): operate on the real project folder. File
        # containment in _resolve then guards against escapes from THAT base.
        return ws.resolve()
    if not (ws / ".git").is_dir():
        if not create:
            raise HTTPException(status_code=404, detail="Workspace not found.")
        with _init_lock:
            if not (ws / ".git").is_dir():  # re-check under the lock
                ws.mkdir(parents=True, exist_ok=True)
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
    return ws


def user_root_for(user_id: str) -> Path:
    """Return the {WORKSPACE_ROOT}/{user_id}/ directory (never creates it)."""
    if not _SAFE_ID.match(user_id):
        raise HTTPException(status_code=400, detail="Invalid user id.")
    return _contained(WORKSPACE_ROOT, user_id)


def _resolve(ws: Path, raw: str) -> Path:
    """Resolve *raw* relative to the workspace; reject traversal."""
    rel_path = Path(raw.replace("\\", "/").strip())
    if str(rel_path) in {"", "."} or rel_path.is_absolute() or ".." in rel_path.parts:
        raise HTTPException(status_code=400, detail="Path outside workspace.")
    candidate = _contained(ws, str(rel_path))
    # Second, stronger runtime check: collapse symlinks and re-verify
    # containment (normpath alone does not follow symlinks).
    resolved = candidate.resolve()
    try:
        rel = resolved.relative_to(ws)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Path outside workspace.") from exc
    if ".git" in rel.parts:
        raise HTTPException(status_code=400, detail="The .git directory is managed.")
    return resolved


# ── file guards ──────────────────────────────────────────────────────────────


def _is_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def _read_text_guarded(resolved: Path, path: str) -> bytes:
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if not resolved.is_file():
        raise HTTPException(status_code=400, detail="Path is a directory.")
    raw = resolved.read_bytes()
    if _is_binary(raw):
        raise HTTPException(
            status_code=415,
            detail="Binary files cannot be edited in Monaco. Use the download button.",
        )
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_FILE_BYTES // 1024} KB Monaco limit.",
        )
    return raw


# ── workspace metadata (named workspaces) ────────────────────────────────────


def _read_meta(ws: Path) -> dict:
    meta_path = ws / _META_FILE
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _write_meta(ws: Path, meta: dict) -> None:
    (ws / _META_FILE).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def git_files(ws: Path) -> list[str]:
    """The workspace's files as the project itself defines them: what git
    sees (tracked + untracked not ignored), sorted, workspace-relative. ONE
    definition for the flat list, the name search and the file count. Never
    an ``os.walk``: the tree can hold ``node_modules`` and no constant may cut
    a listing (a silent cap read a present file as absent, measured)."""
    names: set[str] = set()
    for extra in (("-z",), ("--others", "--exclude-standard", "-z")):
        result = _git(ws, "ls-files", *extra)
        if result.returncode == 0:
            names.update(os.fsdecode(n) for n in result.stdout.split(b"\0") if n)
    names.discard(_META_FILE)
    return sorted(n for n in names if n)


def _count_files(ws: Path) -> int:
    return len(git_files(ws))


def _exclude_meta(ws: Path) -> None:
    """Hide the meta file via .git/info/exclude — local-only ignore that never
    touches the user's tracked .gitignore (clone/linked workspaces are THEIR
    repos; we do not edit their files)."""
    exclude = ws / ".git" / "info" / "exclude"
    current = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    if _META_FILE not in current:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        joiner = "" if (not current or current.endswith("\n")) else "\n"
        exclude.write_text(current + joiner + _META_FILE + "\n", encoding="utf-8")


# ── workspace origins: clone / link ──────────────────────────────────────────


def _clone_into(
    ws: Path, url: str, token: str | None, branch: str | None = None
) -> None:
    """Born-from-repo workspace: git clone (https only). The token travels as a
    transient header for this one command and is never stored on disk.

    ``branch`` es la INTENCIÓN del usuario al montar el workspace y forma parte
    de su contrato: el clon durable nace en esa rama, el sandbox se materializa
    en esa rama y el registro se adelanta en esa rama. Sin ella el clon cae en
    la rama por defecto del remoto y todo lo de abajo termina sincronizando lo
    que casualmente esté checkout, que no es lo que el usuario eligió."""
    if not _SAFE_REPO_URL.match(url):
        raise HTTPException(status_code=400, detail="Repo URL must be https.")
    if branch and not _SAFE_REF.match(branch):
        raise HTTPException(status_code=400, detail="Invalid branch name.")
    ws.parent.mkdir(parents=True, exist_ok=True)
    args = ["git"]
    if token:
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        args += ["-c", f"http.extraHeader=Authorization: Basic {basic}"]
    args += ["clone", "-q"]
    if branch:
        args += ["--branch", branch]
    args += ["--", url, str(ws)]
    try:
        result = subprocess.run(args, capture_output=True, timeout=180)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503, detail="git is not installed in this image."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="git clone timed out.") from exc
    if result.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail="git clone failed: "
            + result.stderr.decode("utf-8", errors="replace")[-300:],
        )
    _git(ws, "config", "user.name", _GIT_IDENTITY[0])
    _git(ws, "config", "user.email", _GIT_IDENTITY[1])
    _exclude_meta(ws)


def _resolve_link_target(local_path: str) -> Path:
    """Contain a user-supplied link target under LINK_ROOT — normpath +
    startswith (the CodeQL-recognized barrier), then a symlink-collapsing
    resolve with a re-check."""
    candidate = os.path.normpath(os.path.join(str(LINK_ROOT), local_path.strip()))
    # SIMPLE guard form on purpose: a compound condition (`!= root and not
    # startswith`) breaks CodeQL's barrier recognition — proven empirically.
    if not candidate.startswith(str(LINK_ROOT) + os.sep):
        raise HTTPException(
            status_code=400,
            detail=f"Local path must live under {LINK_ROOT}.",
        )
    resolved = Path(candidate).resolve()
    if not str(resolved).startswith(str(LINK_ROOT) + os.sep):
        raise HTTPException(status_code=400, detail="Local path escapes the link root.")
    if not resolved.is_dir():
        raise HTTPException(
            status_code=400, detail=f"Local path not found: {local_path}"
        )
    return resolved


def _link_into(ws: Path, local_path: str) -> Path:
    """Linked workspace (dev only): the workspace IS an existing local folder —
    the Claude-Desktop model. In prod the backend cannot see the user's disk;
    repo_url (git as transport) is the equivalent there. Returns the target."""
    if config.APP_ENV != "dev":
        raise HTTPException(
            status_code=400,
            detail="local_path links are dev-only; use repo_url in prod.",
        )
    target = _resolve_link_target(local_path)
    ws.parent.mkdir(parents=True, exist_ok=True)
    if ws.exists():
        raise HTTPException(
            status_code=409,
            detail="Workspace already exists; choose a different name.",
        )
    ws.symlink_to(target, target_is_directory=True)
    if not (target / ".git").is_dir():
        for cmd in (
            ("init", "-q"),
            ("config", "user.name", _GIT_IDENTITY[0]),
            ("config", "user.email", _GIT_IDENTITY[1]),
            ("commit", "--allow-empty", "-q", "-m", "init workspace"),
        ):
            result = _git(target, *cmd)
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail="Workspace git init failed: "
                    + result.stderr.decode("utf-8", errors="replace"),
                )
    # Pre-existing repos keep THEIR committer identity — we set nothing.
    _exclude_meta(target)
    return target


# ── Public git-read helpers ───────────────────────────────────────────────────
# Used by workspace_router endpoints and by any backend code that needs to
# inspect the state of a workspace without going through the MCP server.


def git_status(ws: Path) -> str:
    """Return `git status --short` output for *ws* (empty string = clean)."""
    result = _git(ws, "status", "--short")
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="git status failed: "
            + result.stderr.decode("utf-8", errors="replace").strip(),
        )
    return result.stdout.decode("utf-8", errors="replace").strip()


def git_diff(ws: Path, path: str = "", staged: bool = False) -> str:
    """Return the diff of uncommitted changes, optionally restricted to *path*.
    Set *staged=True* for the index diff. Output is capped at 64 KB."""
    args: list[str] = ["diff"]
    if staged:
        args.append("--cached")
    if path:
        resolved = _resolve(ws, path)
        args += ["--", str(resolved)]
    result = _git(ws, *args)
    output = result.stdout.decode("utf-8", errors="replace")
    return output[:65536] + ("\n... (truncated)" if len(output) > 65536 else "")


def git_log(ws: Path, max_entries: int = 20) -> list[dict]:
    """Return the last *max_entries* (capped at 100) commits as dicts with
    keys: hash, author, date, message."""
    n = max(1, min(max_entries, 100))
    result = _git(ws, "log", f"-{n}", "--pretty=format:%H\x1f%an\x1f%ai\x1f%s")
    entries: list[dict] = []
    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
        parts = line.split("\x1f", 3)
        if len(parts) == 4:
            entries.append(
                {
                    "hash": parts[0][:12],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3],
                }
            )
    return entries


def git_current_branch(ws: Path) -> str:
    """Return the active branch name or '(detached) <sha>' if HEAD is detached."""
    result = _git(ws, "symbolic-ref", "--short", "HEAD")
    if result.returncode == 0:
        return result.stdout.decode("utf-8", errors="replace").strip()
    rev = _git(ws, "rev-parse", "--short", "HEAD")
    return "(detached) " + rev.stdout.decode("utf-8", errors="replace").strip()


def git_list_branches(ws: Path) -> list[str]:
    """Return all local branch names; active branch has a leading '*'."""
    result = _git(ws, "branch", "--list")
    return [
        line.strip()
        for line in result.stdout.decode("utf-8", errors="replace").splitlines()
        if line.strip()
    ]


def search_content(ws: Path, pattern: str, path: str = "") -> list[str]:
    """Grep for *pattern* (case-insensitive literal) across tracked and
    untracked files, optionally restricted to *path*. Returns up to 200
    matching lines as 'rel/path:lineno:text'."""
    if not pattern:
        raise HTTPException(status_code=400, detail="Empty search pattern.")
    base = str(_resolve(ws, path)) if path else str(ws)
    result = _git(
        ws,
        "grep",
        "-i",
        "-n",
        "--untracked",
        "--no-index",
        "-e",
        pattern,
        "--",
        base,
    )
    lines = result.stdout.decode("utf-8", errors="replace").splitlines()
    ws_prefix = str(ws) + os.sep
    rel_lines = [
        (line.replace(ws_prefix, "") if line.startswith(ws_prefix) else line)
        for line in lines[:200]
    ]
    return rel_lines


# ── Public write helpers ──────────────────────────────────────────────────────
# Every write helper commits atomically so the workspace history stays clean.
# They are synchronous (same as workspace_for/_git) — call from a thread pool
# executor when invoked from async contexts if latency matters.


def _git_commit_all(ws: Path, message: str) -> None:
    """Stage everything and commit.  Skipped gracefully when nothing changed."""
    _git(ws, "config", "user.name", _GIT_IDENTITY[0])
    _git(ws, "config", "user.email", _GIT_IDENTITY[1])
    _git(ws, "add", "-A")
    # Exit-code 0 from diff --cached --quiet means nothing staged.
    if _git(ws, "diff", "--cached", "--quiet").returncode == 0:
        return
    result = _git(ws, "commit", "-q", "-m", message)
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="git commit failed: "
            + result.stderr.decode("utf-8", errors="replace").strip(),
        )


def write_file(ws: Path, rel_path: str, content: bytes | str) -> Path:
    """Write *content* to *ws/rel_path* (create or overwrite) and commit.
    *content* may be bytes (binary/text) or str (auto-encoded as UTF-8).
    Returns the resolved absolute path."""
    dest = _resolve(ws, rel_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = content if isinstance(content, bytes) else content.encode("utf-8")
    dest.write_bytes(data)
    _git_commit_all(ws, f"agent: write {rel_path}")
    return dest


def create_file(ws: Path, rel_path: str, content: bytes | str) -> Path:
    """Like write_file but raises 409 if the file already exists."""
    dest = _resolve(ws, rel_path)
    if dest.exists():
        raise HTTPException(
            status_code=409,
            detail=f"File already exists: '{rel_path}'. Use write_file to overwrite.",
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = content if isinstance(content, bytes) else content.encode("utf-8")
    dest.write_bytes(data)
    _git_commit_all(ws, f"agent: create {rel_path}")
    return dest


def update_file(ws: Path, rel_path: str, content: bytes | str) -> Path:
    """Like write_file but raises 404 if the file does not exist."""
    dest = _resolve(ws, rel_path)
    if not dest.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: '{rel_path}'. Use create_file to create it.",
        )
    if not dest.is_file():
        raise HTTPException(
            status_code=400, detail=f"Path is a directory: '{rel_path}'."
        )
    data = content if isinstance(content, bytes) else content.encode("utf-8")
    dest.write_bytes(data)
    _git_commit_all(ws, f"agent: update {rel_path}")
    return dest


def delete_file(ws: Path, rel_path: str) -> None:
    """Delete *ws/rel_path* (file or empty directory) and commit the removal."""
    target = _resolve(ws, rel_path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: '{rel_path}'.")
    if target.is_dir():
        if any(target.iterdir()):
            raise HTTPException(
                status_code=400,
                detail=f"Directory '{rel_path}' is not empty. Delete its contents first.",
            )
        target.rmdir()
    else:
        target.unlink()
    _git_commit_all(ws, f"agent: delete {rel_path}")
