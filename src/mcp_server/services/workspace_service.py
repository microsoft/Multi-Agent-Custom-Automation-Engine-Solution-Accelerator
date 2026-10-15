"""
Workspace tools — the agents' EYES and HANDS on the per-user workspace.

Arquitectura: PERSISTENCIA y COMPUTACIÓN son dos lugares distintos.

    Azure Files (durable)                       Sandbox local (efímero)
    {MACAE_WORKSPACE_ROOT}/{user}/{ws}/         {MACAE_SANDBOX_ROOT}/{user}/{ws}/
    └── repo git = ORIGEN durable       clone   └── working tree sobre el que
        lo que el frontend muestra     ──────►      REALMENTE se trabaja
        lo que sobrevive al contenedor              .venv, node_modules, caches,
                                       ◄──────      builds, pytest/mypy/ruff,
                                        push        git, shell, herramientas
                                     (aprobado)     instaladas al vuelo

Por qué: el share es un montaje SMB. No admite enlaces simbólicos (ningún venv
puede existir ahí), git lo rechaza por "dubious ownership", `rmtree` falla a
mitad con ENOTEMPTY y cada I/O paga red. Todo eso es computación y no tiene
por qué tocar el share. El share guarda lo único que debe sobrevivir: el repo,
sus commits y lo que el usuario ve. El sandbox se destruye con el contenedor y
se rematerializa desde el share con un clone; lo que no se publicó, se
perdió, y eso es correcto: lo publicado es lo aprobado.

La RAMA y el REPOSITORIO son intención del usuario al montar el workspace y
viven en su metadato (`.macae_workspace_meta.json`: ``repo_url``, ``branch``):
el clon durable nace en esa rama, el sandbox se materializa en esa rama con ese
repositorio como ``upstream``, y publish y el fast-forward del registro la
conservan. Nada de abajo mira el HEAD circunstancial ni el ``origin`` del share.

Flujo de cada tool: `_sandbox(user_id, workspace_id)` materializa (clone si no
existe; fast-forward desde el share si el sandbox está limpio) y devuelve el
working tree local. Las tools de escritura commitean en el sandbox y PUBLICAN
(push al share, que acepta con `receive.denyCurrentBranch=updateInstead` si
su árbol está limpio). `workspace_exec` corre en el sandbox y no publica nada:
lo que un comando deje sin commitear es efímero. `workspace_publish` empuja lo
pendiente de forma explícita.

Read tools (3): workspace_list_entries, workspace_read_file, workspace_search_files
Git-read tools (6): workspace_search_content, workspace_git_status,
    workspace_git_diff, workspace_git_log, workspace_git_current_branch,
    workspace_git_list_branches
Write tools (4): workspace_write_file, workspace_create_file,
    workspace_update_file, workspace_delete_file
Exec (1): workspace_exec   Publish (1): workspace_publish

Security: identical containment forms as the backend service — normpath +
SIMPLE `startswith(base + os.sep)` guards (the only shape CodeQL recognizes
as a py/path-injection barrier; compound conditions break recognition),
followed by a symlink-collapsing resolve + re-check. Linked workspaces
(symlinks under the user root) resolve to their target like the backend does;
el sandbox se clona desde ese target igual que desde el share.
"""

import json
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

from core.factory import Domain, MCPToolBase
from utils.formatters import format_error_response, format_success_response

WORKSPACE_ROOT = Path(os.getenv("MACAE_WORKSPACE_ROOT") or str(Path.home() / ".macae" / "workspaces")).resolve()
#: Disco LOCAL del contenedor. Aquí vive la computación; nada de esto tiene
#: que sobrevivir a un reinicio, porque se rematerializa desde el share.
SANDBOX_ROOT = Path(os.getenv("MACAE_SANDBOX_ROOT") or str(Path.home() / ".macae" / "sandboxes")).resolve()
MAX_FILE_BYTES = 1 * 1024 * 1024  # 1 MB — same read cap as the backend
MAX_ENTRIES = 200
_META_FILE = ".macae_workspace_meta.json"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,127}$")
# Mismo contrato de nombre de rama que el backend (la rama declarada al montar).
_SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./~^-]{0,63}$")
_GIT_IDENTITY = ("MACAE Workspace", "workspace@macae.local")

# ── terminal (workspace_exec) ────────────────────────────────────────────────
# Kill switch: set MACAE_WORKSPACE_EXEC=0 to disable the shell tool entirely.
EXEC_ENABLED = os.getenv("MACAE_WORKSPACE_EXEC", "1") != "0"
EXEC_TIMEOUT_DEFAULT = 120
EXEC_TIMEOUT_MAX = 600
EXEC_OUTPUT_LIMIT = 60000  # chars per stream, then truncated with a marker
# Env vars whose NAME suggests a credential are stripped from the child process:
# the agent gets a real terminal, not the server's secrets.
_SECRET_ENV_HINT = re.compile(r"SECRET|PASSWORD|PASSWD|TOKEN|_KEY$|APIKEY|CREDENTIAL", re.I)


class WorkspaceAccessError(Exception):
    """Raised for any invalid/denied workspace access; message is user-safe."""


def _workspace_dir(user_id: str, workspace_id: str) -> Path:
    """Resolve an EXISTING workspace (read-only: never creates)."""
    if not user_id or not _SAFE_ID.match(user_id):
        raise WorkspaceAccessError(f"Invalid user_id: '{user_id}'.")
    if not workspace_id or not _SAFE_ID.match(workspace_id):
        raise WorkspaceAccessError(f"Invalid workspace_id: '{workspace_id}'.")
    joined = os.path.normpath(os.path.join(str(WORKSPACE_ROOT), user_id, workspace_id))
    if not joined.startswith(str(WORKSPACE_ROOT) + os.sep):
        raise WorkspaceAccessError("Workspace path escapes the root.")
    ws = Path(joined)
    if ws.is_symlink():  # linked workspace → operate on the real project
        if os.getenv("APP_ENV", "dev") != "dev":
            raise WorkspaceAccessError("Linked workspaces are dev-only.")
        link_root = Path(os.getenv("MACAE_LINK_ROOT", "/workspaces")).resolve()
        target = ws.resolve()
        if not str(target).startswith(str(link_root) + os.sep):
            raise WorkspaceAccessError("Linked workspace escapes the link root.")
        ws = target
    elif not ws.is_dir():
        raise WorkspaceAccessError(f"Workspace '{workspace_id}' does not exist for this user.")
    return ws


def _resolve_in(ws: Path, raw: str) -> Path:
    ws = ws.resolve()
    rel = Path((raw or "").replace("\\", "/").strip())
    if str(rel) in {"", "."}:
        return ws
    if rel.is_absolute() or ".." in rel.parts:
        raise WorkspaceAccessError("Path outside workspace.")
    joined = os.path.normpath(os.path.join(str(ws), str(rel)))
    if not joined.startswith(str(ws) + os.sep):
        raise WorkspaceAccessError("Path outside workspace.")
    resolved = Path(joined).resolve()
    if not str(resolved).startswith(str(ws) + os.sep):
        raise WorkspaceAccessError("Path outside workspace.")
    if ".git" in resolved.relative_to(ws).parts:
        raise WorkspaceAccessError("The .git directory is managed.")
    return resolved


def _git(ws: Path, *args: str, trust: tuple[Path, ...] = ()) -> "subprocess.CompletedProcess[bytes]":
    # ``safe.directory`` acotado a ESTE árbol (y a los ``trust`` que una
    # operación de dos repos necesite, como clone o push contra el share):
    # sobre el share el dueño no es el uid del proceso y git lo rechaza con
    # "detected dubious ownership". Pre-flight, no manejo del error.
    safe: list[str] = []
    for path in (ws, *trust):
        safe += ["-c", f"safe.directory={path}"]
    try:
        return subprocess.run(
            ["git", *safe, *args],
            cwd=ws,
            capture_output=True,
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise WorkspaceAccessError("git is not available in this environment.") from exc
    except subprocess.TimeoutExpired as exc:
        raise WorkspaceAccessError("git operation timed out.") from exc


def _git_commit_all(ws: Path, message: str) -> bool:
    """Stage all changes in *ws* and commit with *message*. Idempotent: if
    nothing changed after staging, the commit is skipped. Returns whether a
    commit was made."""
    _git(ws, "config", "user.name", _GIT_IDENTITY[0])
    _git(ws, "config", "user.email", _GIT_IDENTITY[1])
    _git(ws, "add", "-A")
    result = _git(ws, "diff", "--cached", "--quiet")
    if result.returncode == 0:
        return False  # nothing staged — no commit needed
    commit_result = _git(ws, "commit", "-q", "-m", message)
    if commit_result.returncode != 0:
        raise WorkspaceAccessError(
            "git commit failed: " + commit_result.stderr.decode("utf-8", errors="replace").strip()
        )
    return True


def _catch_up(sandbox: Path, share: Path) -> tuple[bool, str]:
    """Antes de publicar, el sandbox se pone al día con la rama del share.

    El share avanza sin el sandbox (otro escritor, un commit del usuario en
    Monaco, el ritual post-merge) y un push desde atrás es un rechazo
    non-fast-forward. Medido 2026-10-14 en local: el agente escribía y
    commiteaba, el push era rechazado y el archivo nunca llegaba al explorador,
    aunque la tool devolviera ``published: false``. Los commits del agente se
    rebasan sobre la punta del share; un conflicto real se aborta y se reporta,
    nunca se resuelve a ciegas.
    """
    branch = _declared_branch(share)
    trust = (share, share / ".git")
    fetched = _git(sandbox, "fetch", "-q", "origin", trust=trust)
    if fetched.returncode != 0:
        return False, fetched.stderr.decode("utf-8", errors="replace").strip()[-400:]
    if _git(sandbox, "rev-parse", "--verify", "-q", f"origin/{branch}").returncode != 0:
        return True, ""  # el share aún no tiene esa rama: nada con qué ponerse al día
    rebased = _git(sandbox, "rebase", "-q", f"origin/{branch}")
    if rebased.returncode == 0:
        return True, ""
    _git(sandbox, "rebase", "--abort")
    detail = rebased.stderr.decode("utf-8", errors="replace").strip()[-300:]
    return False, "the durable tree advanced and the agent's changes conflict with it: " + detail


def _commit_and_publish(user_id: str, workspace_id: str, sandbox: Path, message: str) -> dict:
    """Commit en el sandbox, puesta al día con el share y push. Lo que devuelve
    va al ``details`` de la tool: el agente sabe si lo que escribió ya es
    visible o quedó local."""
    committed = _git_commit_all(sandbox, message)
    share = _workspace_dir(user_id, workspace_id)
    ok, detail = _catch_up(sandbox, share)
    if ok:
        ok, detail = _publish(sandbox, share)
    return {"committed": committed, "published": ok, "publish_detail": detail}


_SANDBOX_LOCKS: dict[str, threading.Lock] = {}
_SANDBOX_LOCKS_GUARD = threading.Lock()


def _sandbox_lock(key: str) -> threading.Lock:
    with _SANDBOX_LOCKS_GUARD:
        return _SANDBOX_LOCKS.setdefault(key, threading.Lock())


def _pid_is_alive(pid: int) -> bool:
    """Un temporal ``.materializing-…-<pid>`` sólo es basura si su dueño ya no
    corre: preguntarle al SO evita borrar el clone en curso de otro proceso que
    comparte ``SANDBOX_ROOT``."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _is_interrupted_clone(sandbox: Path) -> bool:
    """``git clone`` escribe ``HEAD -> refs/heads/.invalid`` al crear el repo y
    lo reemplaza al terminar: encontrarlo es la firma de un clone cortado."""
    try:
        return (sandbox / ".git" / "HEAD").read_text(encoding="utf-8").strip() == "ref: refs/heads/.invalid"
    except OSError:
        return False


def _sandbox_path(user_id: str, workspace_id: str) -> Path:
    """Ruta LOCAL del sandbox, con la misma contención que el share."""
    joined = os.path.normpath(os.path.join(str(SANDBOX_ROOT), user_id, workspace_id))
    if not joined.startswith(str(SANDBOX_ROOT) + os.sep):
        raise WorkspaceAccessError("Sandbox path escapes the root.")
    return Path(joined)


def _read_meta(share: Path) -> dict:
    """El contrato del workspace que el backend escribió al montarlo: ``name``,
    ``repo_url`` y ``branch``. Es la única fuente durable de la intención del
    usuario; de ahí salen el ``upstream`` y la rama del sandbox."""
    try:
        return json.loads((share / _META_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _declared_branch(share: Path) -> str:
    """La rama declarada al montar; si el workspace es anterior a ese contrato,
    la rama actual del share."""
    branch = str(_read_meta(share).get("branch") or "").strip()
    return branch if branch and _SAFE_REF.match(branch) else _share_branch(share)


def _share_branch(share: Path) -> str:
    done = _git(share, "symbolic-ref", "--short", "HEAD")
    if done.returncode != 0:
        raise WorkspaceAccessError("The workspace repository has no current branch.")
    return done.stdout.decode("utf-8", errors="replace").strip()


def _sandbox_is_clean(sandbox: Path) -> bool:
    """Sin cambios locales y sin commits que el share no tenga."""
    status = _git(sandbox, "status", "--porcelain")
    if status.returncode != 0 or status.stdout.strip():
        return False
    ahead = _git(sandbox, "rev-list", "--count", "@{u}..HEAD")
    return ahead.returncode == 0 and ahead.stdout.decode().strip() == "0"


def _sandbox(user_id: str, workspace_id: str) -> Path:
    """El working tree LOCAL del workspace: se materializa desde el share.

    - No existe → `git clone <share> <sandbox>`; el share queda como ``origin``
      y, si el share tiene su propio ``origin`` (GitHub), ése queda como
      ``upstream`` en el sandbox.
    - Existe y está limpio → fast-forward desde el share, para que lo que el
      usuario cambió en Monaco llegue al agente.
    - Existe y tiene trabajo local → se deja tal cual: el trabajo del agente
      nunca se pisa.
    El share tiene que ser un repo git (el backend lo garantiza al crearlo).
    """
    share = _workspace_dir(user_id, workspace_id)
    if _git(share, "rev-parse", "--is-inside-work-tree").returncode != 0:
        raise WorkspaceAccessError("Workspace is not a git repository; it must be initialized by the backend first.")
    meta = _read_meta(share)
    branch = str(meta.get("branch") or "").strip()
    if branch and not _SAFE_REF.match(branch):
        branch = ""
    upstream = str(meta.get("repo_url") or "").strip()
    sandbox = _sandbox_path(user_id, workspace_id)
    # Al clonar/fetch/push contra el share, git valida la propiedad del ORIGEN
    # por su gitdir: hay que confiar el árbol y su .git, no sólo el árbol.
    share_trust = (share, share / ".git")
    with _sandbox_lock(str(sandbox)):
        # El share acepta pushes sobre su rama actual actualizando su árbol si
        # está limpio: así lo publicado aparece en el frontend sin más pasos.
        _git(share, "config", "receive.denyCurrentBranch", "updateInstead")
        # El resto de un clone que no terminó lleva la marca que git pone hasta
        # el final: ``HEAD -> refs/heads/.invalid``. No es un sandbox: se
        # descarta; no se reutiliza ni se "repara".
        if _is_interrupted_clone(sandbox):
            shutil.rmtree(sandbox, ignore_errors=True)
        if not (sandbox / ".git").is_dir():
            sandbox.parent.mkdir(parents=True, exist_ok=True)
            # Materialización TRANSACCIONAL: se clona en un temporal al lado, se
            # verifica HEAD y recién entonces se renombra al lugar (atómico). Lo
            # que falle o se interrumpa se borra; nunca queda a medias con el
            # nombre del sandbox. ``--shared``: el sandbox toma los objetos del
            # share en vez de copiarlos (medido 2026-10-10: 3 s vs 26 s y 272 KB
            # vs 195 MB). El share es el origen durable; el sandbox, efímero.
            # Restos de materializaciones de otros procesos (caídos a mitad):
            # ``SANDBOX_ROOT`` puede estar compartido y ``_sandbox_lock`` sólo
            # excluye a hilos de este proceso, así que un temporal cuyo dueño
            # sigue vivo es el clone EN CURSO de otro proceso, no basura: sólo
            # se descartan los huérfanos (su PID ya no corre).
            for stale in sandbox.parent.glob(f".materializing-{sandbox.name}-*"):
                owner = stale.name.rsplit("-", 1)[-1]
                if owner.isdigit() and _pid_is_alive(int(owner)):
                    continue
                shutil.rmtree(stale, ignore_errors=True)
            staging = sandbox.parent / f".materializing-{sandbox.name}-{os.getpid()}"
            try:
                # En la rama DECLARADA al montar, no en la que el share tenga checkout.
                done = _git(
                    sandbox.parent,
                    "clone",
                    "-q",
                    "--shared",
                    *(["--branch", branch] if branch else []),
                    "--",
                    str(share),
                    str(staging),
                    trust=(*share_trust, staging),
                )
                if done.returncode != 0:
                    raise WorkspaceAccessError(
                        "Could not materialize the workspace: " + done.stderr.decode("utf-8", errors="replace").strip()
                    )
                # El repositorio se termina de configurar ANTES de ocupar el
                # nombre del sandbox: lo que se promueve ya está completo.
                setup_commands: list[tuple[str, ...]] = [
                    ("config", "user.name", _GIT_IDENTITY[0]),
                    ("config", "user.email", _GIT_IDENTITY[1]),
                ]
                if upstream:
                    setup_commands.append(("remote", "add", "upstream", upstream))
                for command in setup_commands:
                    configured = _git(staging, *command)
                    if configured.returncode != 0:
                        detail = configured.stderr.decode("utf-8", errors="replace").strip()
                        raise WorkspaceAccessError("Could not configure the workspace sandbox: " + detail)
                # El clone terminó y el repo está configurado (un share vacío,
                # sin commits, también es válido): recién ahora ocupa el nombre
                # del sandbox, de forma atómica.
                staging.rename(sandbox)
            except BaseException:
                shutil.rmtree(staging, ignore_errors=True)
                raise
        elif _sandbox_is_clean(sandbox):
            _git(sandbox, "fetch", "-q", "origin", trust=share_trust)
            _git(sandbox, "merge", "-q", "--ff-only", "@{u}")
    return sandbox


def _publish(sandbox: Path, share: Path) -> tuple[bool, str]:
    """Empuja HEAD del sandbox a la rama actual del share. ``(ok, detalle)``.

    Un rechazo no es un fallo del agente: normalmente el árbol del share está
    sucio (el usuario editó en Monaco sin commitear) y dos escritores sin
    acuerdo no se resuelven a ciegas. Se reporta y se deja al humano.
    """
    branch = _declared_branch(share)
    done = _git(sandbox, "push", "-q", "origin", f"HEAD:refs/heads/{branch}", trust=(share, share / ".git"))
    if done.returncode == 0:
        return True, f"published to '{branch}'"
    return False, done.stderr.decode("utf-8", errors="replace").strip()[-400:]


def _child_env(trust: Path | None = None) -> dict:
    """Environment for spawned commands: the server's env minus anything whose
    name looks like a credential.

    ``trust`` declara un árbol de confianza para git en el hijo
    (``GIT_CONFIG_*``): un ``git`` corrido por ``workspace_exec`` no pasa por
    ``_git``, así que sin esto el agente vuelve a chocar con "detected dubious
    ownership" sobre el share aunque las tools de git funcionen.
    """
    env = {k: v for k, v in os.environ.items() if not _SECRET_ENV_HINT.search(k)}
    if trust is not None:
        env |= {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": str(trust),
        }
    return env


def _clip(text: str) -> tuple[str, bool]:
    """Cap one output stream; returns (text, was_truncated)."""
    if len(text) <= EXEC_OUTPUT_LIMIT:
        return text, False
    return text[:EXEC_OUTPUT_LIMIT] + "\n... (output truncated)", True


class WorkspaceToolService(MCPToolBase):
    """Workspace tools for agents — list, read, search, git-read, and write."""

    def __init__(self):
        super().__init__(Domain.WORKSPACE)

    def register_tools(self, mcp) -> None:
        # ── READ TOOLS ────────────────────────────────────────────────────

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        def workspace_list_entries(user_id: str, workspace_id: str, path: str = "") -> str:
            """List ONE directory level of the user's project workspace
            (directories first). Call with path='' for the root, then with a
            directory path to descend. user_id and workspace_id are MANDATORY
            — use the values given in your instructions."""
            try:
                ws = _sandbox(user_id, workspace_id)
                base = _resolve_in(ws, path)
                if not base.is_dir():
                    raise WorkspaceAccessError(f"Not a directory: {path}")
                dirs: list[dict] = []
                files: list[dict] = []
                for entry in sorted(base.iterdir(), key=lambda e: e.name.lower()):
                    if entry.name == ".git" or entry.name == _META_FILE:
                        continue
                    if len(dirs) + len(files) >= MAX_ENTRIES:
                        break
                    if entry.is_dir():
                        dirs.append({"name": entry.name, "type": "directory"})
                    else:
                        files.append(
                            {
                                "name": entry.name,
                                "type": "file",
                                "size": entry.stat().st_size,
                            }
                        )
                return format_success_response(
                    action="workspace_list_entries",
                    details={"path": path or "/", "entries": dirs + files},
                    summary=f"{len(dirs)} directories, {len(files)} files in "
                    f"'{path or '/'}' of workspace '{workspace_id}'.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_list_entries")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_list_entries")

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        def workspace_read_file(user_id: str, workspace_id: str, path: str) -> str:
            """Read a TEXT file from the user's project workspace and return its
            full content. Binary files and files over 1 MB are refused. user_id
            and workspace_id are MANDATORY — use the values from your
            instructions."""
            try:
                ws = _sandbox(user_id, workspace_id)
                resolved = _resolve_in(ws, path)
                if not resolved.is_file():
                    raise WorkspaceAccessError(f"File not found: {path}")
                raw = resolved.read_bytes()
                if b"\x00" in raw[:8192]:
                    raise WorkspaceAccessError(f"Binary file (cannot read): {path}")
                if len(raw) > MAX_FILE_BYTES:
                    raise WorkspaceAccessError(f"File exceeds 1 MB limit: {path}")
                return format_success_response(
                    action="workspace_read_file",
                    details={
                        "path": path,
                        "content": raw.decode("utf-8", errors="replace"),
                    },
                    summary=f"Read {len(raw)} bytes from '{path}'.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_read_file")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_read_file")

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        def workspace_search_files(user_id: str, workspace_id: str, query: str) -> str:
            """Find files by name across the WHOLE workspace (case-insensitive
            substring on the relative path; git is the index). Returns up to
            200 matching paths. user_id and workspace_id are MANDATORY."""
            try:
                ws = _sandbox(user_id, workspace_id)
                q = (query or "").strip().lower()
                if not q:
                    raise WorkspaceAccessError("Empty query.")
                names: set[str] = set()
                for extra in ((), ("--others", "--exclude-standard")):
                    result = _git(ws, "ls-files", *extra)
                    if result.returncode == 0:
                        names.update(result.stdout.decode("utf-8", errors="replace").splitlines())
                names.discard(_META_FILE)
                matches = sorted(p for p in names if q in p.lower())[:MAX_ENTRIES]
                return format_success_response(
                    action="workspace_search_files",
                    details={"query": query, "matches": matches},
                    summary=f"{len(matches)} files match '{query}' in workspace '{workspace_id}'.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_search_files")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_search_files")

        # ── GIT-READ TOOLS ────────────────────────────────────────────────

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        def workspace_search_content(user_id: str, workspace_id: str, pattern: str, path: str = "") -> str:
            """Grep for *pattern* (literal string, case-insensitive) inside tracked
            and untracked files. Optionally restrict to a sub-path (relative to
            the workspace root). Returns up to 200 matching lines as
            'rel/path:lineno:text'. Returns an empty list when nothing matches."""
            try:
                ws = _sandbox(user_id, workspace_id)
                if not pattern:
                    raise WorkspaceAccessError("Empty pattern.")
                # git grep --untracked searches tracked + untracked files.
                # --no-index is INCOMPATIBLE with --untracked (git fatal error).
                # Pathspec must be RELATIVE to the repo root, not an absolute path.
                args = ["grep", "-i", "-n", "--untracked", "-e", pattern]
                if path:
                    # Resolve to validate containment, then make relative.
                    resolved = _resolve_in(ws, path)
                    rel = str(resolved.relative_to(ws))
                    args += ["--", rel]
                result = _git(ws, *args)
                # rc=0 → matches found; rc=1 → no matches (not an error); rc>1 → error
                if result.returncode > 1:
                    stderr = result.stderr.decode("utf-8", errors="replace").strip()
                    raise WorkspaceAccessError(f"git grep failed: {stderr}")
                lines = result.stdout.decode("utf-8", errors="replace").splitlines()
                rel_lines = lines[:MAX_ENTRIES]
                return format_success_response(
                    action="workspace_search_content",
                    details={
                        "pattern": pattern,
                        "path": path or "/",
                        "matches": rel_lines,
                    },
                    summary=f"{len(rel_lines)} matching lines for '{pattern}'.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_search_content")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_search_content")

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        def workspace_git_status(user_id: str, workspace_id: str) -> str:
            """Return the short git status of the workspace (staged, unstaged,
            untracked files). Equivalent to `git status --short`."""
            try:
                ws = _sandbox(user_id, workspace_id)
                result = _git(ws, "status", "--short")
                if result.returncode != 0:
                    stderr = result.stderr.decode("utf-8", errors="replace").strip()
                    raise WorkspaceAccessError(f"git status failed: {stderr}")
                output = result.stdout.decode("utf-8", errors="replace").strip()
                return format_success_response(
                    action="workspace_git_status",
                    details={"status": output or "(clean)"},
                    summary="Git status retrieved.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_git_status")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_git_status")

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        def workspace_git_diff(user_id: str, workspace_id: str, path: str = "", staged: bool = False) -> str:
            """Show the diff of uncommitted changes. Set staged=true to see
            staged (indexed) changes. Optionally restrict to a sub-path.
            Output is capped at 64 KB."""
            try:
                ws = _sandbox(user_id, workspace_id)
                args = ["diff"]
                if staged:
                    args.append("--cached")
                if path:
                    target = _resolve_in(ws, path)
                    args += ["--", str(target)]
                result = _git(ws, *args)
                output = result.stdout.decode("utf-8", errors="replace")
                if len(output) > 65536:
                    output = output[:65536] + "\n... (truncated)"
                return format_success_response(
                    action="workspace_git_diff",
                    details={
                        "staged": staged,
                        "path": path or "/",
                        "diff": output or "(no changes)",
                    },
                    summary="Git diff retrieved.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_git_diff")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_git_diff")

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        def workspace_git_log(user_id: str, workspace_id: str, max_entries: int = 20) -> str:
            """Return the last *max_entries* (capped at 100) git commits in the
            workspace as a list of {hash, author, date, message}."""
            try:
                ws = _sandbox(user_id, workspace_id)
                n = max(1, min(max_entries, 100))
                result = _git(
                    ws,
                    "log",
                    f"-{n}",
                    "--pretty=format:%H\x1f%an\x1f%ai\x1f%s",
                )
                entries = []
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
                return format_success_response(
                    action="workspace_git_log",
                    details={"entries": entries},
                    summary=f"{len(entries)} commit(s) retrieved.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_git_log")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_git_log")

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        def workspace_git_current_branch(user_id: str, workspace_id: str) -> str:
            """Return the name of the currently checked-out branch (or the
            detached HEAD SHA if not on a branch)."""
            try:
                ws = _sandbox(user_id, workspace_id)
                result = _git(ws, "symbolic-ref", "--short", "HEAD")
                if result.returncode == 0:
                    branch = result.stdout.decode("utf-8", errors="replace").strip()
                else:
                    rev = _git(ws, "rev-parse", "--short", "HEAD")
                    branch = "(detached) " + rev.stdout.decode("utf-8", errors="replace").strip()
                return format_success_response(
                    action="workspace_git_current_branch",
                    details={"branch": branch},
                    summary=f"Current branch: {branch}",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_git_current_branch")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_git_current_branch")

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        def workspace_git_list_branches(user_id: str, workspace_id: str) -> str:
            """List all local branches in the workspace. The active branch is
            marked with a leading '*'."""
            try:
                ws = _sandbox(user_id, workspace_id)
                result = _git(ws, "branch", "--list")
                branches = [
                    line.strip()
                    for line in result.stdout.decode("utf-8", errors="replace").splitlines()
                    if line.strip()
                ]
                return format_success_response(
                    action="workspace_git_list_branches",
                    details={"branches": branches},
                    summary=f"{len(branches)} branch(es) found.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_git_list_branches")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_git_list_branches")

        # ── WRITE TOOLS ───────────────────────────────────────────────────

        @mcp.tool(tags={self.domain.value})
        def workspace_write_file(
            user_id: str,
            workspace_id: str,
            path: str,
            content: str,
            commit_message: str = "",
        ) -> str:
            """Write (create or overwrite) a text file at *path* inside the
            workspace and commit the change. Use workspace_create_file when you
            want an explicit guard against overwriting. commit_message is
            optional — a default is generated from the path."""
            try:
                ws = _sandbox(user_id, workspace_id)
                dest = _resolve_in(ws, path)
                dest.parent.mkdir(parents=True, exist_ok=True)
                data = content.encode("utf-8")
                if len(data) > MAX_FILE_BYTES:
                    raise WorkspaceAccessError(f"File too large ({len(data)} bytes). Max is {MAX_FILE_BYTES} bytes.")
                dest.write_bytes(data)
                msg = commit_message.strip() or f"agent: write {path}"
                pub = _commit_and_publish(user_id, workspace_id, ws, msg)
                return format_success_response(
                    action="workspace_write_file",
                    details={"path": path, "bytes": len(data), **pub},
                    summary=f"Wrote {len(data)} bytes to '{path}'; {pub['publish_detail']}.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_write_file")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_write_file")

        @mcp.tool(tags={self.domain.value})
        def workspace_create_file(
            user_id: str,
            workspace_id: str,
            path: str,
            content: str,
            commit_message: str = "",
        ) -> str:
            """Create a NEW text file at *path* inside the workspace and commit.
            Fails if the file already exists — use workspace_write_file to
            overwrite."""
            try:
                ws = _sandbox(user_id, workspace_id)
                dest = _resolve_in(ws, path)
                if dest.exists():
                    raise WorkspaceAccessError(f"File already exists: '{path}'. Use workspace_write_file to overwrite.")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                msg = commit_message.strip() or f"agent: create {path}"
                pub = _commit_and_publish(user_id, workspace_id, ws, msg)
                return format_success_response(
                    action="workspace_create_file",
                    details={"path": path, "bytes": len(content.encode("utf-8")), **pub},
                    summary=f"Created '{path}' ({len(content.encode('utf-8'))} bytes); {pub['publish_detail']}.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_create_file")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_create_file")

        @mcp.tool(tags={self.domain.value})
        def workspace_update_file(
            user_id: str,
            workspace_id: str,
            path: str,
            content: str,
            commit_message: str = "",
        ) -> str:
            """Update an EXISTING text file at *path* with new *content* and
            commit. Fails if the file does not exist — use workspace_create_file
            to create it first."""
            try:
                ws = _sandbox(user_id, workspace_id)
                dest = _resolve_in(ws, path)
                if not dest.exists():
                    raise WorkspaceAccessError(f"File not found: '{path}'. Use workspace_create_file to create it.")
                if not dest.is_file():
                    raise WorkspaceAccessError(f"Path is a directory: '{path}'.")
                dest.write_text(content, encoding="utf-8")
                msg = commit_message.strip() or f"agent: update {path}"
                pub = _commit_and_publish(user_id, workspace_id, ws, msg)
                return format_success_response(
                    action="workspace_update_file",
                    details={"path": path, "bytes": len(content.encode("utf-8")), **pub},
                    summary=f"Updated '{path}' ({len(content.encode('utf-8'))} bytes); {pub['publish_detail']}.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_update_file")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_update_file")

        @mcp.tool(tags={self.domain.value})
        def workspace_delete_file(
            user_id: str,
            workspace_id: str,
            path: str,
            commit_message: str = "",
        ) -> str:
            """Delete a file (or empty directory) at *path* from the workspace
            and commit the removal. Directories are only deleted when empty."""
            try:
                ws = _sandbox(user_id, workspace_id)
                target = _resolve_in(ws, path)
                if not target.exists():
                    raise WorkspaceAccessError(f"Path not found: '{path}'.")
                if target.is_dir():
                    if any(target.iterdir()):
                        raise WorkspaceAccessError(f"Directory '{path}' is not empty. Delete its contents first.")
                    target.rmdir()
                else:
                    target.unlink()
                msg = commit_message.strip() or f"agent: delete {path}"
                pub = _commit_and_publish(user_id, workspace_id, ws, msg)
                return format_success_response(
                    action="workspace_delete_file",
                    details={"path": path, **pub},
                    summary=f"Deleted '{path}'; {pub['publish_detail']}.",
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_delete_file")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_delete_file")

        # ── TERMINAL ──────────────────────────────────────────────────────

        @mcp.tool(tags={self.domain.value})
        def workspace_exec(
            user_id: str,
            workspace_id: str,
            command: str,
            path: str = "",
            timeout: int = EXEC_TIMEOUT_DEFAULT,
        ) -> str:
            """Run a shell command in the workspace's local sandbox — a REAL terminal.

            The sandbox is a clone of the workspace on local disk: install
            dependencies (`uv sync`, `npm ci`), run tests, build, run scripts.
            All of it is fast and none of it touches the durable workspace.
            Nothing a command leaves uncommitted survives the sandbox; call
            workspace_publish to keep results, or use the write tools, which
            publish on their own.

            The command runs through bash with the sandbox as the working
            directory, so pipes, globs, redirections and && all work:
            `git status`, `git diff HEAD~1`, `git log --oneline -10`,
            `git commit -am "msg"`, `uv run pytest -q`, `npm ci && npm run build`,
            `find . -name '*.py'`, `grep -rn TODO src | head -20`,
            `python script.py`.

            Prefer THIS over asking for a dedicated tool — it is the generic
            capability. Returns exit_code, stdout and stderr verbatim: a
            non-zero exit_code is a real command result (e.g. failing tests),
            not a tool failure, so read it and report it faithfully instead of
            guessing.

            path (optional) runs the command in a sub-directory of the
            workspace. timeout is in seconds (default 120, max 600)."""
            try:
                if not EXEC_ENABLED:
                    raise WorkspaceAccessError("Shell execution is disabled on this server (MACAE_WORKSPACE_EXEC=0).")
                if not (command or "").strip():
                    raise WorkspaceAccessError("Empty command.")
                ws = _sandbox(user_id, workspace_id)
                cwd = _resolve_in(ws, path) if path else ws
                if not cwd.is_dir():
                    raise WorkspaceAccessError(f"Not a directory: '{path}'.")
                secs = max(1, min(int(timeout or EXEC_TIMEOUT_DEFAULT), EXEC_TIMEOUT_MAX))
                try:
                    proc = subprocess.run(
                        ["bash", "-c", command],
                        cwd=str(cwd),
                        capture_output=True,
                        timeout=secs,
                        env=_child_env(ws),
                    )
                except FileNotFoundError as exc:
                    raise WorkspaceAccessError("bash is not available in this environment.") from exc
                except subprocess.TimeoutExpired as exc:
                    raise WorkspaceAccessError(f"Command timed out after {secs}s: {command[:120]}") from exc
                out, out_cut = _clip(proc.stdout.decode("utf-8", errors="replace"))
                err, err_cut = _clip(proc.stderr.decode("utf-8", errors="replace"))
                rel_cwd = "/" if cwd == ws else str(cwd.relative_to(ws))
                return format_success_response(
                    action="workspace_exec",
                    details={
                        "command": command,
                        "cwd": rel_cwd,
                        "exit_code": proc.returncode,
                        "stdout": out,
                        "stderr": err,
                        "truncated": out_cut or err_cut,
                    },
                    summary=(f"exit={proc.returncode} for `{command[:80]}` in '{rel_cwd}'."),
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_exec")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_exec")

        @mcp.tool(tags={self.domain.value})
        def workspace_publish(user_id: str, workspace_id: str, commit_message: str = "") -> str:
            """Publish the sandbox's pending work to the durable workspace: commit
            any uncommitted changes (commit_message optional) and push to the
            workspace repository, which is what the user sees. Use it after
            workspace_exec produced files worth keeping (a build, a generated
            module, a fix applied by a script): exec never publishes by itself,
            so anything left uncommitted in the sandbox is ephemeral.

            The push is refused when the durable working tree has uncommitted
            edits of its own (the user changed files in the editor): that is
            reported, not forced, because two writers do not get merged blind."""
            try:
                ws = _sandbox(user_id, workspace_id)
                msg = commit_message.strip() or "agent: publish sandbox work"
                pub = _commit_and_publish(user_id, workspace_id, ws, msg)
                head = _git(ws, "rev-parse", "--short", "HEAD").stdout.decode().strip()
                return format_success_response(
                    action="workspace_publish",
                    details={"head": head, **pub},
                    summary=(f"Published {head}." if pub["published"] else f"Not published: {pub['publish_detail']}"),
                )
            except WorkspaceAccessError as e:
                return format_error_response(error_message=str(e), context="workspace_publish")
            except Exception as e:
                return format_error_response(error_message=str(e), context="workspace_publish")

    @property
    def tool_count(self) -> int:
        return 15
