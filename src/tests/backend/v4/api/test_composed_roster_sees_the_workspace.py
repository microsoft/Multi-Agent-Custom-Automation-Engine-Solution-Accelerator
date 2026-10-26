"""Un equipo compuesto para trabajar sobre un workspace tiene que poder leerlo.

Medido en producción el 2026-09-19 (rev 0000130, plan c7ab4b24, sesión
autonoma-001): el Router escaló con ``WORKSPACE_ID=multi-agent-custom-
automation-engine-solution-accelerator`` y compuso
``RepositoryAuditAgent(mcp=False) ValidationAgent(mcp=False)
DevSecOpsAuditAgent(mcp=False)``. En los cinco minutos del run hubo CERO
llamadas a herramientas de workspace, y la "auditoría" resultante describía un
``config.yaml``, un ``requirements.txt`` con ``pyaudio``/``speechrecognition`` y
un ``Dockerfile`` que no existen en el árbol. Sin herramientas no leyó otro
árbol: no leyó ninguno.

La causa está en el esquema de ``run_plan``: ``use_mcp`` se describe como "true
ONLY if it needs external systems or live data" y no figura en ``required``, así
que para auditar el repositorio del propio usuario el Router lo omite. El
docstring de ``_team_from_router_roster`` ya fija la regla —"Factory constraints
are re-checked HERE, in code (the prompt orients the Router; it guarantees
nothing)"—; a ese re-chequeo le faltaba el acceso al workspace.
"""

import importlib

import pytest

router = importlib.import_module("v4.api.router")

WS = "multi-agent-custom-automation-engine-solution-accelerator"

# El roster real de la 0000130, tal cual lo emitió el Router: sin use_mcp.
ROSTER = [
    {
        "name": "RepositoryAuditAgent",
        "description": "Audita la estructura del repositorio",
        "system_message": "Revisa el árbol del proyecto.",
        "use_reasoning": True,
    },
    {
        "name": "ValidationAgent",
        "description": "Ejecuta validaciones no destructivas",
        "system_message": "Corre las pruebas y los linters.",
        "coding_tools": True,
    },
    {
        "name": "DevSecOpsAuditAgent",
        "description": "Revisa CI/CD y seguridad",
        "system_message": "Revisa los workflows.",
        "use_reasoning": True,
    },
]


class FakeStore:
    """Sólo la capa Cosmos: el TeamService y el modelo son los reales."""

    def __init__(self):
        self.saved = []

    async def get_team(self, team_id):
        return None

    async def add_team(self, team_config):
        self.saved.append(team_config)

    async def update_team(self, team_config):
        self.saved.append(team_config)


async def compose(roster, workspace_id):
    return await router._team_from_router_roster(
        roster, "audita el proyecto", "u1", FakeStore(), workspace_id
    )


def by_name(team):
    return {a.name: a for a in team.agents}


@pytest.mark.asyncio
async def test_a_roster_composed_for_a_workspace_can_read_it():
    """Todo especialista ve el workspace, incluido el que lleva coding_tools:
    el workspace no se sacrifica por el code interpreter; ambos conviven."""
    agents = by_name(await compose(ROSTER, WS))

    assert all(agents[a["name"]].use_mcp for a in ROSTER)
    assert agents["ValidationAgent"].coding_tools is True


@pytest.mark.asyncio
async def test_the_clarification_channel_stays_a_channel():
    """ProxyAgent es el canal humano; darle herramientas lo vuelve un agente."""
    team = await compose(ROSTER, WS)

    assert by_name(team)["ProxyAgent"].use_mcp is False


@pytest.mark.asyncio
async def test_without_a_workspace_nothing_is_granted():
    """Sin workspace montado no hay contrato que conformar: no se concede nada."""
    team = await compose(ROSTER, None)

    assert not any(a.use_mcp for a in team.agents)


@pytest.mark.asyncio
async def test_reasoning_agents_are_composed_on_the_reasoning_deployment():
    """Medido 2026-10-01: gpt-4.1-mini rechaza ``reasoning.effort`` (400). Un
    agente con ``use_reasoning`` sale del roster con ``REASONING_MODEL_NAME``;
    los demás con el deployment por defecto. El flag y el modelo son una sola
    decisión, tomada por lo que la tarea requiere."""
    from common.config.app_config import config

    agents = by_name(await compose(ROSTER, WS))
    reasoning = config.REASONING_MODEL_NAME
    assert agents["RepositoryAuditAgent"].deployment_name == reasoning
    assert agents["DevSecOpsAuditAgent"].deployment_name == reasoning
    assert agents["ValidationAgent"].deployment_name != reasoning


@pytest.mark.asyncio
async def test_a_specialist_that_must_search_the_web_gets_the_native_web_search():
    # La fábrica ya publica WebSearchTool con ``use_web_search``; el roster lo
    # ofrecía sólo como ``use_bing``, y el investigador de un sequential nacía
    # sin web (medido 2026-10-20: "no tengo acceso a web browsing").
    team = await compose(
        [
            {
                "name": "WebResearchAgent",
                "description": "Busca novedades en la web",
                "system_message": "Busca y cita fuentes.",
                "use_web_search": True,
            }
        ],
        None,
    )
    agent = by_name(team)["WebResearchAgent"]
    assert agent.use_web_search is True
    assert agent.use_bing is False
