"""Incremento 4: revalidación de INC, el primer controlador que origina trabajo.

El registro (``docs/incidents/*.json``) es la definición del trabajo: el
invariante, la sonda ejecutable, el techo de autoridad y la fecha de
vencimiento. ``work_events`` es su historial, con identidad
``<incident_id>:<expires_if_not_reverified_by>`` (la ocurrencia es el valor de
la fecha, no el reloj):

- ``incident_expiry``  la fecha venció; una ocurrencia por vencimiento (409).
- ``human_authority``  la decisión humana cuando la sonda excede el techo.
- ``reconciled``       la evidencia y el estado operacional resultante.

Git no se escribe: el estado vivo es el pliegue de ``reconciled``
(``operational_state``); avanzar la fecha en el registro es un PR.

Veredicto de la sonda: ``exit_code == 0`` es señal sana; cualquier otro deja el
INC en ``needs_revalidation`` con ``operational=false``. Sin shell aquí: la
capacidad ``execute(command, cwd)`` la inyecta quien arma el reconciliador
(en producción ``workspace_exec`` de ca-mcp sobre el workspace del registro).
"""

import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from common.services.event_store import EventStore, TransitionError

logger = logging.getLogger(__name__)

KIND_EXPIRY = "incident_expiry"
KIND_AUTHORITY = "human_authority"
KIND_RECONCILED = "reconciled"
# Orden de autoridad del schema incident.v1 (authority_ceiling y actions.class).
ACTION_CLASSES = ("read-only", "write-scratch", "write-shared")
EVIDENCE_TAIL = 4000


@dataclass(frozen=True)
class Evidence:
    exit_code: int
    stdout: str
    stderr: str
    #: Commit del registro contra el que corrió la sonda. Sin esto un
    #: ``reconciled`` dice "sano" sin decir de qué árbol, y un registro viejo
    #: produce alarmas falsas en silencio.
    source: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout[-EVIDENCE_TAIL:],
            "stderr": self.stderr[-EVIDENCE_TAIL:],
            "source": self.source,
        }


Executor = Callable[[str, str], Awaitable[Evidence]]
Registry = Callable[[], Awaitable[list[dict[str, Any]]]]
#: Vinculación diferida: devuelve ``(registry, execute)`` cuando el registro ya
#: es alcanzable, o ``None`` si todavía no existe. Que el registro esté o no
#: NO es un hecho del arranque —el clon llega al share cuando alguien lo crea
#: desde la UI—, así que el intento se repite; uno solo dejaba el loop sin
#: origen de trabajo para toda la vida del proceso.
Provider = Callable[[], tuple[Registry, Executor] | None]
#: Señales vivas ya disparadas, normalizadas a lo mínimo estable que llega con
#: una alerta: ``{"id", "rule", "dimensions"}``. La normalización vive en quien
#: habla con Azure, no acá: este módulo empareja, no interpreta payloads.
AlertSource = Callable[[], Awaitable[list[dict[str, Any]]]]


def utcnow() -> datetime:
    return datetime.now(UTC)


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def expiry_identity(incident: dict[str, Any]) -> str:
    return (
        f"{incident['incident_id']}:{incident['learn']['expires_if_not_reverified_by']}"
    )


def is_due(incident: dict[str, Any], now: datetime) -> bool:
    return _parse(incident["learn"]["expires_if_not_reverified_by"]) <= now


def exceeds_ceiling(probe_class: str, ceiling: dict[str, Any]) -> bool:
    return ACTION_CLASSES.index(probe_class) > ACTION_CLASSES.index(
        ceiling["max_action_class_without_human"]
    )


async def rearm_due(
    incidents: Iterable[dict[str, Any]], store: EventStore, now: datetime
) -> int:
    """Apila ``incident_expiry`` por cada INC vencido; devuelve los nuevos."""
    produced = 0
    for incident in incidents:
        probe = (incident.get("learn") or {}).get("executable_probe")
        if not probe or not is_due(incident, now):
            continue
        result = await store.append(
            KIND_EXPIRY,
            expiry_identity(incident),
            {
                "incident_id": incident["incident_id"],
                "probe": probe,
                "ceiling": incident["authority_ceiling"],
            },
        )
        if not result.duplicate:
            produced += 1
            logger.info("INC %s vencido: evento %s", incident["incident_id"], result.id)
    return produced


async def _run_probe(
    event: dict[str, Any], *, store: EventStore, execute: Executor | None
) -> Evidence:
    """Techo → (autoridad humana si hace falta) → sonda → evidencia.

    Compartido por las dos entradas al ciclo: el vencimiento (proactivo) y la
    detección por alerta (reactivo). La sonda es la única confirmación que el
    código puede hacer: ``structural_match`` es semántico y no se evalúa solo.
    """
    identity, payload = event["identity"], event["payload"]
    incident_id, probe, ceiling = (
        payload["incident_id"],
        payload["probe"],
        payload["ceiling"],
    )
    if execute is None:
        raise TransitionError(f"{incident_id}: sin capacidad de ejecución configurada")
    if exceeds_ceiling(probe["class"], ceiling):
        decision = await store.find(KIND_AUTHORITY, identity)
        if decision is None:
            raise TransitionError(
                f"{incident_id}: sonda {probe['class']} excede el techo "
                f"{ceiling['max_action_class_without_human']}; espera human_authority"
            )
        if decision["payload"].get("decision") != "approve":
            raise RuntimeError(f"{incident_id}: sonda rechazada por humano")
    return await execute(probe["command_or_test"], probe.get("cwd", ""))


async def apply_incident_expiry(
    event: dict[str, Any], *, store: EventStore, execute: Executor | None
) -> None:
    """La transición: techo → sonda → evidencia → ``reconciled``."""
    identity, payload = event["identity"], event["payload"]
    incident_id = payload["incident_id"]
    evidence = await _run_probe(event, store=store, execute=execute)
    operational = evidence.exit_code == 0
    await store.append(
        KIND_RECONCILED,
        identity,
        {
            "incident_id": incident_id,
            "operational": operational,
            "status": "verified" if operational else "needs_revalidation",
            "evidence": evidence.to_payload(),
        },
    )
    logger.info(
        "INC %s revalidado: %s (exit=%d)",
        incident_id,
        "sano" if operational else "needs_revalidation",
        evidence.exit_code,
    )


async def operational_state(
    store: EventStore, incident: dict[str, Any]
) -> dict[str, Any] | None:
    """Pliegue del ``reconciled`` de este vencimiento: el estado vivo, no git."""
    doc = await store.find(KIND_RECONCILED, expiry_identity(incident))
    if doc is None:
        return None
    return {**doc["payload"], "last_verified": doc.get("_ts") or doc.get("created_at")}


# ── carril reactivo: una señal viva contra el universo de firmas ─────────────
# El carril proactivo entra por el reloj (`expires_if_not_reverified_by` →
# `rearm_due` → incident_expiry): "llegó el momento contractual de volver a
# probar algo conocido". Éste entra por una señal: "apareció algo compatible con
# una firma conocida". Son causas distintas, así que son eventos distintos.

KIND_DETECTED = "incident_detected"
#: Señal real sin firma que la reconozca: la cola de candidatos a INC. Sin este
#: hecho el sistema vio algo nuevo y no dejó rastro ("0 emparejan" era silencio).
KIND_UNMATCHED = "incident_unmatched"


def detection_identity(incident_id: str, alert_id: str) -> str:
    """Identidad del hecho reactivo: la firma MÁS la instancia que la disparó.

    No alcanza con ``incident_id``: el mismo incidente reaparece muchas veces y
    cada aparición es un hecho propio. La instancia de la alerta es lo único
    estable que llega con la señal.
    """
    return f"{incident_id}:{alert_id}"


def candidates(
    rule: str, dimensions: dict[str, str], incidents: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Los incidentes cuyo ``signature.alert_match`` encaja con esta alerta.

    Selección de CANDIDATO, no prueba de identidad: un mismo código en una misma
    ruta puede venir de otra causa. Un binding encaja si es de la misma regla y
    todas sus dimensiones aparecen con el mismo valor en la alerta (subconjunto:
    la alerta puede traer más dimensiones que las que la firma declara).
    Devuelve 0, 1 o N; con N el emparejamiento es ambiguo y quien llama decide.
    """
    hit = []
    for incident in incidents:
        for binding in (incident.get("signature") or {}).get("alert_match") or []:
            if binding["rule"] != rule:
                continue
            if all(dimensions.get(k) == v for k, v in binding["dimensions"].items()):
                hit.append(incident)
                break
    return hit


async def match_alerts(
    alerts: Iterable[dict[str, Any]],
    incidents: Iterable[dict[str, Any]],
    store: EventStore,
) -> int:
    """Apila ``incident_detected`` por cada (firma candidata, alerta); nuevos.

    Idempotente por identidad: la misma alerta re-leída en el barrido siguiente
    choca con 409 y no vuelve a originar trabajo.
    """
    known = list(incidents)
    produced = 0
    for alert in alerts:
        matched = candidates(alert["rule"], alert.get("dimensions") or {}, known)
        if not matched:
            await store.append(
                KIND_UNMATCHED,
                alert["id"],
                {
                    "alert_id": alert["id"],
                    "rule": alert["rule"],
                    "dimensions": alert.get("dimensions") or {},
                },
            )
            continue
        for incident in matched:
            probe = (incident.get("learn") or {}).get("executable_probe")
            if not probe:
                continue
            result = await store.append(
                KIND_DETECTED,
                detection_identity(incident["incident_id"], alert["id"]),
                {
                    "incident_id": incident["incident_id"],
                    "alert_id": alert["id"],
                    "rule": alert["rule"],
                    "dimensions": alert.get("dimensions") or {},
                    "ambiguous_with": [
                        other["incident_id"]
                        for other in matched
                        if other["incident_id"] != incident["incident_id"]
                    ],
                    "probe": probe,
                    "ceiling": incident["authority_ceiling"],
                },
            )
            if not result.duplicate:
                produced += 1
                logger.info(
                    "Alerta %s compatible con INC %s: evento %s",
                    alert["rule"],
                    incident["incident_id"],
                    result.id,
                )
    return produced


async def apply_incident_detected(
    event: dict[str, Any], *, store: EventStore, execute: Executor | None
) -> None:
    """La confirmación: se corre la sonda de la firma candidata.

    La sonda es lo único que el código puede comprobar; ``structural_match`` es
    semántico. Sonda en rojo ⇒ la firma REPRODUCE y la alerta queda explicada
    por ese incidente. Sonda en verde ⇒ el invariante se sostiene y esa alerta
    tiene otra causa: se deja el hecho registrado y NO se atribuye.
    """
    identity, payload = event["identity"], event["payload"]
    incident_id = payload["incident_id"]
    evidence = await _run_probe(event, store=store, execute=execute)
    reproduced = evidence.exit_code != 0
    await store.append(
        KIND_RECONCILED,
        identity,
        {
            "incident_id": incident_id,
            "alert_id": payload["alert_id"],
            "operational": not reproduced,
            "status": "reproduced" if reproduced else "not_reproduced",
            "ambiguous_with": payload.get("ambiguous_with") or [],
            "evidence": evidence.to_payload(),
        },
    )
    logger.info(
        "INC %s ante la alerta %s: %s (exit=%d)",
        incident_id,
        payload["rule"],
        "reproduce" if reproduced else "no reproduce",
        evidence.exit_code,
    )
