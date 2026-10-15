"""Registro y ejecución del incremento 4 con las piezas que ya existen.

- Registro: el backend monta el mismo share que ca-mcp (``MACAE_WORKSPACE_ROOT``)
  y ``workspace_for(user_id, workspace_id)`` es el único resolutor. Los INC se
  leen del clon en disco, ``docs/incidents/*.json``, con ``_resolve`` como
  contención; no hay red para leer un archivo local.
- Ejecución: la misma vía que un agente. ``ReconnectingMCPTool`` sobre
  ``MCPConfig.from_env()`` y ``call_tool("workspace_exec", ...)``; la evidencia
  es ``exit_code``/``stdout``/``stderr`` verbatim del payload de la tool
  (``format_success_response``). Un error de la tool es fallo de capacidad.

El registro se descubre por CONTENIDO, no por configuración: es el workspace
que contiene ``docs/incidents``. Nada que declarar, nada que marcar, nada que
poner en variables de entorno: se clona el repo en un workspace desde la UI y
el reconciliador lo encuentra.

Un mismo registro puede ser alcanzable bajo VARIAS identidades (el mismo clon
enlazado desde varios ``user_id``). Eso sigue siendo UN registro: los
candidatos se agrupan por la ruta física que resuelven.

Entre registros DISTINTOS se desempata en dos pasos, con lo ya declarado y sin
adivinar: el ``workspace_id`` canónico (``INCIDENT_REGISTRY_WORKSPACE_ID``, por
defecto ``incident-registry``) primero, y después la identidad de trabajo
(``INCIDENT_REGISTRY_USER_ID``), que desempata globalmente y no sólo entre
alias de una misma ruta. Dos clones del mismo repo NO se colapsan por su
``origin``: pueden estar en ramas o commits distintos y darlos por equivalentes
taparía una divergencia real. Si tras los dos pasos queda más de uno, el
reconciliador se detiene y los nombra en el log.
"""

import json
import logging
import os
import shlex
import subprocess
from typing import Any

from agent_framework import MCPStreamableHTTPTool

from v4.common.mcp_tool import ReconnectingMCPTool
from v4.common.services.workspace_service import (
    _SAFE_ID,
    _SAFE_REF,
    REGISTRY_WORKSPACE_ID,
    WORKSPACE_ROOT,
    _read_meta,
    _resolve,
    workspace_for,
)
from v4.control.incident_revalidation import Evidence, Executor, Registry
from v4.magentic_agents.models.agent_models import MCPConfig

logger = logging.getLogger(__name__)

INCIDENTS_DIR = "docs/incidents"
EXEC_TIMEOUT_SECONDS = 600


class WorkspaceCapability:
    def __init__(
        self,
        *,
        user_id: str,
        workspace_id: str,
        tool: MCPStreamableHTTPTool | None = None,
        owned: bool = False,
    ) -> None:
        self.user_id = user_id
        self.workspace_id = workspace_id
        self._tool = tool
        #: Commit del registro leído en el último ``registry()``.
        self.source = ""
        #: Se adelanta el registro que ``discover()`` ELIGIÓ, y sólo ése.
        #: Antes esto se decidía por el NOMBRE del workspace
        #: (``incident-registry``): como nadie lo bautiza así —un usuario crea
        #: el workspace con un nombre y una URL, no conoce el concepto de
        #: workspace_id— el adelanto no corría nunca y el clon se podría
        #: (medido en prod: clon en un commit anterior a ``docs/incidents``).
        #: El nombre sigue sirviendo, pero sólo como desempate en ``discover``.
        #: Adelantar es ``--ff-only``: no reescribe ni descarta nada; ante
        #: divergencia falla, se registra y el registro se lee como está.
        self.owned = owned
        #: Una condición estable se registra al cambiar, no en cada vuelta.
        self._said_foreign = False

    async def _mcp(self) -> MCPStreamableHTTPTool:
        if self._tool is None:
            cfg = MCPConfig.from_env()
            tool = ReconnectingMCPTool(
                name=cfg.name, description=cfg.description, url=cfg.url
            )
            await tool.__aenter__()
            self._tool = tool
        return self._tool

    async def aclose(self) -> None:
        if self._tool is not None:
            try:
                await self._tool.close()
            except Exception as ex:  # cierre cruzado de tarea, como en lifecycle
                logger.debug("MCP tool close: %s", ex)
            self._tool = None

    def _head(self, ws: Any) -> str:
        """Commit del clon. El backend monta el mismo share, así que es git local."""
        try:
            # Mismo pre-flight que ``_git``: sobre el share el dueño del árbol no
            # es el uid del proceso y git aborta por "dubious ownership", con lo
            # que ``source`` quedaba vacío y la evidencia no decía de qué árbol
            # salió el veredicto.
            done = subprocess.run(
                ["git", "-c", f"safe.directory={ws}", "rev-parse", "HEAD"],
                cwd=ws,
                capture_output=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as ex:
            logger.warning("HEAD del registro ilegible: %s", ex)
            return ""
        return done.stdout.decode().strip() if done.returncode == 0 else ""

    async def _fast_forward(self) -> None:  # noqa: D401
        """Adelanta el registro antes de leerlo: un clon que nadie sincroniza es
        una foto que se pudre y cada merge lo deja más atrás.

        Sólo en el registro que ``discover()`` eligió; cualquier otro workspace
        se lee tal cual. ``--ff-only`` es la garantía: no reescribe historia ni
        descarta commits, y si el árbol divergió git falla, se registra el motivo
        y se sigue con lo que hay; el commit queda en la evidencia, así que un
        registro viejo se delata en vez de mentir en silencio."""
        if not self.owned:
            if not self._said_foreign:
                self._said_foreign = True
                logger.info(
                    "Registro en un workspace ajeno (%s): se lee tal cual, sin "
                    "adelantar",
                    self.workspace_id,
                )
            return
        # La rama es la que el usuario DECLARÓ al montar el workspace (meta del
        # share), no el HEAD circunstancial del sandbox: sincronizar "lo que
        # esté checkout ahora" no describe ninguna intención. Un workspace
        # anterior a este contrato no la tiene en el meta: se cae al HEAD y se
        # dice una vez.
        declared = str(
            _read_meta(workspace_for(self.user_id, self.workspace_id)).get("branch")
            or ""
        ).strip()
        if declared and not _SAFE_REF.match(declared):
            logger.warning(
                "Rama declarada inválida en el meta (%r); se ignora", declared
            )
            declared = ""
        if not declared and not getattr(self, "_said_no_branch", False):
            self._said_no_branch = True
            logger.info(
                "Workspace %s sin rama declarada en su meta: el adelanto usa el HEAD "
                "del sandbox (workspace anterior al contrato de rama)",
                self.workspace_id,
            )
        branch_expr = (
            shlex.quote(declared) if declared else "$(git rev-parse --abbrev-ref HEAD)"
        )
        try:
            # El comando corre en el SANDBOX del MCP (clon local del share):
            # ahí `origin` es el share y `upstream` es el repositorio declarado
            # al montar. Se adelanta desde upstream y se publica al share, que es
            # lo que el usuario ve y lo que este backend lee del disco. Un
            # workspace nacido vacío no tiene upstream: no hay de dónde
            # adelantar y eso no es un fallo.
            evidence = await self.execute(
                # Pre-flight, no manejo del error: sólo se hace merge si la rama
                # declarada existe en upstream; si no, es un hecho que se
                # reporta con nombre.
                "if ! git remote get-url upstream >/dev/null 2>&1; then "
                "echo 'sin upstream: nada que adelantar'; exit 0; fi; "
                f"b={branch_expr} && "
                # El share (origin) es la verdad del usuario; el sandbox del
                # registro es computación desechable. Si el share se recreó
                # (borrar y volver a montar el workspace), el sandbox queda
                # DETRÁS y el push se rechaza como non-fast-forward (prod
                # 2026-10-03: exit 1 "behind its remote"). Se alinea a origin
                # antes de adelantar; sólo si está limpio y sin commits que el
                # share no tenga (`checkout -B` resetea la rama y un HEAD
                # suelto queda huérfano): trabajo local nunca se pisa, se
                # reporta con nombre.
                "git fetch --quiet origin && "
                "if ! git diff --quiet || ! git diff --cached --quiet; then "
                "echo 'sandbox con cambios locales: no se adelanta'; exit 0; fi; "
                'if git rev-parse --verify --quiet "refs/heads/$b" >/dev/null && '
                '[ -n "$(git rev-list -n 1 "refs/heads/$b" --not "origin/$b")" ]; then '
                'echo "sandbox con commits sin publicar en $b: no se adelanta"; exit 0; fi; '
                "if ! git symbolic-ref -q HEAD >/dev/null && "
                '[ -n "$(git rev-list -n 1 HEAD --not --branches --remotes)" ]; then '
                "echo 'sandbox con commits sueltos sin publicar: no se adelanta'; exit 0; fi; "
                # Con las guardas de arriba ya pasadas (árbol limpio, nada sin
                # publicar), alinear la rama a la punta del share no pisa nada:
                # es lo que evita el rechazo non-fast-forward del push final
                # cuando el sandbox quedó detrás del share.
                'git checkout --quiet -B "$b" "origin/$b" && '
                "git fetch --quiet upstream && "
                'if ! git rev-parse --verify --quiet "refs/remotes/upstream/$b" >/dev/null; then '
                'echo "upstream no tiene la rama $b: nada que adelantar"; exit 0; fi; '
                'git merge --ff-only --quiet "upstream/$b" && '
                # origin es el share por ruta local: git arranca su receive-pack
                # SIN la configuración del cliente (local_repo_env), y sobre un
                # árbol de otro uid muere por dubious ownership; el cliente lo
                # reporta como "Could not read from remote repository" (prod:
                # 647 veces en 3 días, INC-2026-013). La confianza viaja en el
                # propio comando del pack.
                "git push --quiet --receive-pack='git -c safe.directory=* receive-pack' "
                'origin "HEAD:refs/heads/$b"',
                "",
            )
        except Exception as ex:  # la capacidad no está disponible: se lee lo que hay
            logger.warning("Registro sin adelantar (%s): %s", type(ex).__name__, ex)
            return
        if evidence.exit_code != 0:
            logger.warning(
                "Registro sin adelantar (exit %d): %s",
                evidence.exit_code,
                (evidence.stderr or evidence.stdout).strip()[-200:],
            )

    async def registry(self) -> list[dict[str, Any]]:
        await self._fast_forward()
        ws = workspace_for(self.user_id, self.workspace_id)
        self.source = self._head(ws)
        base = _resolve(ws, INCIDENTS_DIR)
        incidents: list[dict[str, Any]] = []
        if not base.is_dir():
            logger.warning("Registro sin %s en %s", INCIDENTS_DIR, ws)
            return incidents
        for path in sorted(base.glob("*.json")):
            try:
                incident = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as ex:
                logger.warning("INC %s ilegible: %s", path.name, ex)
                continue
            if isinstance(incident, dict) and "incident_id" in incident:
                incidents.append(incident)
        return incidents

    async def execute(self, command: str, cwd: str) -> Evidence:
        tool = await self._mcp()
        raw = await tool.call_tool(
            "workspace_exec",
            user_id=self.user_id,
            workspace_id=self.workspace_id,
            command=command,
            path="" if cwd in ("", ".", "/") else cwd,
            timeout=EXEC_TIMEOUT_SECONDS,
        )
        text = (
            raw
            if isinstance(raw, str)
            else "".join(getattr(c, "text", "") or "" for c in raw)
        )
        # ca-mcp responde éxito y error con UN envelope JSON:
        # {"status", "action", "summary", "details"}. Un error de la tool es
        # fallo de CAPACIDAD (no evidencia) y su motivo viene en ``summary``.
        # Un texto que no sea ese JSON también es fallo de capacidad, con el
        # texto como motivo: nunca se adivina por el primer carácter.
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            raise RuntimeError(f"workspace_exec: {text[:500]}") from None
        if not isinstance(payload, dict) or payload.get("status") != "success":
            reason = (
                payload.get("summary") or payload.get("message")
                if isinstance(payload, dict)
                else None
            )
            raise RuntimeError(f"workspace_exec: {reason or text[:500]}")
        details = payload["details"]
        return Evidence(
            exit_code=int(details["exit_code"]),
            stdout=str(details.get("stdout", "")),
            stderr=str(details.get("stderr", "")),
            source=self.source,
        )


def _declared_user() -> str:
    """``INCIDENT_REGISTRY_USER_ID``: la identidad de trabajo del reconciliador."""
    return (os.environ.get("INCIDENT_REGISTRY_USER_ID") or "").strip()


def _pick_identity(aliases: list[tuple[str, str]]) -> tuple[str, str]:
    """De varios alias del MISMO registro, la identidad con la que se trabaja.

    El reconciliador no tiene identidad propia: usa la que sale de aquí para
    llamar ``workspace_exec`` en ca-mcp, así que el ``user_id`` elegido tiene
    que ser uno bajo el que el workspace es alcanzable. Todos los alias lo son.
    ``INCIDENT_REGISTRY_USER_ID`` desempata cuando está declarado; si no, el
    primero en orden, que es estable entre arranques.
    """
    declared = _declared_user()
    if declared:
        for alias in aliases:
            if alias[0] == declared:
                return alias
        if len(aliases) > 1:
            logger.info(
                "INCIDENT_REGISTRY_USER_ID=%s no está entre los alias del "
                "registro (%s); se toma el primero.",
                declared,
                ", ".join(u for u, _ in aliases),
            )
    return aliases[0]


def discover() -> WorkspaceCapability | None:
    """El workspace que contiene ``docs/incidents``. ``None`` si no hay ninguno
    o si hay varios: con varios no se adivina, se nombran en el log."""
    if not WORKSPACE_ROOT.is_dir():
        logger.info("Registro de INC: no existe la raíz %s", WORKSPACE_ROOT)
        return None
    # Candidatos por CONTENIDO, agrupados por la ruta FÍSICA que resuelven: el
    # mismo registro alcanzable bajo varias identidades (un clon montado y
    # enlazado desde varios user_id) es UN registro, no varios. Comparar
    # nombres lo contaba como ambigüedad y el reconciliador no originaba
    # trabajo nunca (medido 2026-09-24: tres alias del mismo directorio).
    by_path: dict[str, list[tuple[str, str]]] = {}
    for user_dir in sorted(
        p for p in WORKSPACE_ROOT.iterdir() if p.is_dir() and _SAFE_ID.match(p.name)
    ):
        for ws in sorted(user_dir.iterdir()):
            # Sólo identidades y workspaces con nombre VÁLIDO. Un borrado que no
            # pudo terminar deja un resto ``.deleting-<id>-<hex>`` con el árbol
            # entero dentro; sin esta cerca contaba como un segundo registro,
            # ``discover`` se declaraba ambiguo y el reconciliador dejaba de
            # originar trabajo por basura que el usuario ya no ve.
            if not _SAFE_ID.match(ws.name):
                continue
            if (ws.is_dir() or ws.is_symlink()) and any(
                (ws / INCIDENTS_DIR).glob("*.json")
            ):
                by_path.setdefault(str(ws.resolve()), []).append(
                    (user_dir.name, ws.name)
                )
    found: list[tuple[str, str]] = [_pick_identity(a) for a in by_path.values()]
    if not found:
        logger.info("Registro de INC: ningún workspace contiene %s", INCIDENTS_DIR)
        return None

    # Desempate entre registros DISTINTOS, en dos pasos y sin adivinar. No se
    # colapsan por ``origin``: dos clones del mismo repo pueden estar en ramas o
    # commits distintos, y darlos por equivalentes taparía una divergencia real
    # (el commit del registro es parte de la evidencia).
    # 1) el nombre canónico del workspace es el primer criterio.
    canonical = [f for f in found if f[1] == REGISTRY_WORKSPACE_ID]
    candidates = canonical or found
    # 2) la identidad declarada desempata GLOBALMENTE lo que quedó, no sólo
    #    entre alias de una misma ruta física: con dos clones distintos (el
    #    ``sample_user`` de dev y el oid real, cada uno con el suyo) el
    #    descubrimiento se declaraba ambiguo aunque la identidad de trabajo
    #    estuviera declarada, que es justo la función que promete.
    declared = _declared_user()
    if len(candidates) > 1 and declared:
        narrowed = [c for c in candidates if c[0] == declared]
        if narrowed:
            candidates = narrowed
        else:
            logger.info(
                "INCIDENT_REGISTRY_USER_ID=%s no está entre los candidatos (%s)",
                declared,
                ", ".join(f"{u}/{w}" for u, w in candidates),
            )

    if len(candidates) > 1:
        logger.warning(
            "Registro de INC ambiguo (%d): %s. El reconciliador no origina "
            "trabajo hasta que quede uno.",
            len(candidates),
            ", ".join(f"{u}/{w}" for u, w in candidates),
        )
        return None

    user_id, workspace_id = candidates[0]
    logger.info(
        "Registro de INC%s: %s/%s",
        " (propio)" if workspace_id == REGISTRY_WORKSPACE_ID else "",
        user_id,
        workspace_id,
    )
    return WorkspaceCapability(user_id=user_id, workspace_id=workspace_id, owned=True)


def bind(capability: WorkspaceCapability) -> tuple[Registry, Executor]:
    return capability.registry, capability.execute


class RegistryProvider:
    """``discover`` + ``bind`` reintentables, dueños de la capacidad que crean.

    El registro es un clon en el share: existe cuando alguien lo crea desde la
    UI, que puede ser mucho después de este arranque. Descubrirlo una sola vez
    dejaba al reconciliador sin registro NI ejecutor hasta el próximo reinicio
    (medido en prod: la revisión viva arrancó con "ningún workspace contiene
    docs/incidents" y quedó así). Devuelve el par la primera vez que vincula y
    ``None`` mientras no haya registro o cuando ya está vinculado.
    """

    def __init__(self) -> None:
        self._capability: WorkspaceCapability | None = None

    def __call__(self) -> tuple[Registry, Executor] | None:
        if self._capability is not None:
            return None
        capability = discover()
        if capability is None:
            return None
        self._capability = capability
        return bind(capability)

    async def aclose(self) -> None:
        if self._capability is not None:
            await self._capability.aclose()
            self._capability = None
