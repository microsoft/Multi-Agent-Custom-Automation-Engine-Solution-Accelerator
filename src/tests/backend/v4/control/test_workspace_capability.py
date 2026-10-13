"""Registro y ejecución del incremento 4 sobre piezas existentes.

Registro: ``workspace_for`` del backend sobre un clon real en ``tmp_path``
(``MACAE_WORKSPACE_ROOT`` apuntado ahí); sólo ``docs/incidents/*.json`` con
``incident_id`` cuentan. Ejecución: ``call_tool("workspace_exec", ...)`` con
un doble que devuelve el JSON exacto de ``format_success_response``; exit≠0
es evidencia, ``status: error`` es fallo de capacidad. Sin referencia durable
en config no hay capacidad.
"""

import json
import subprocess

import pytest

import v4.common.services.workspace_service as ws_mod
import v4.control.workspace_capability as wc
from v4.control.workspace_capability import (
    REGISTRY_WORKSPACE_ID,
    WorkspaceCapability,
    discover,
)

INC = {
    "incident_id": "INC-2026-004",
    "authority_ceiling": {"max_action_class_without_human": "read-only"},
    "learn": {
        "executable_probe": {
            "class": "read-only",
            "cwd": ".",
            "command_or_test": "true",
        }
    },
}


class FakeTool:
    def __init__(self):
        self.calls = []

    async def call_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        if kwargs["command"] == "boom":
            # El envelope de error de ca-mcp: el MISMO que el de éxito, con
            # status "error" y el motivo en summary.
            return json.dumps(
                {
                    "status": "error",
                    "action": "workspace_exec",
                    "summary": "Workspace not found",
                }
            )
        return json.dumps(
            {
                "status": "success",
                "action": tool_name,
                "details": {
                    "command": kwargs["command"],
                    "cwd": kwargs["path"] or "/",
                    "exit_code": 3,
                    "stdout": "out",
                    "stderr": "err",
                    "truncated": False,
                },
            }
        )

    async def close(self):
        pass


@pytest.fixture
def clone(tmp_path, monkeypatch):
    root = tmp_path / "workspaces"
    monkeypatch.setattr(ws_mod, "WORKSPACE_ROOT", root)
    monkeypatch.setattr(wc, "WORKSPACE_ROOT", root)
    ws = root / "reg-user" / "macae-clone"
    (ws / "docs" / "incidents" / "probes").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(ws)], check=True)
    (ws / "docs" / "incidents" / "INC-2026-004.x.json").write_text(json.dumps(INC))
    (ws / "docs" / "incidents" / "README.md").write_text("no")
    (ws / "docs" / "incidents" / "schema.json").write_text(json.dumps({"$schema": "x"}))
    return ws


@pytest.fixture
def cap(clone):
    return WorkspaceCapability(
        user_id="reg-user", workspace_id="macae-clone", tool=FakeTool()
    )


@pytest.mark.asyncio
async def test_registry_reads_incidents_from_the_clone_on_the_share(cap):
    assert [i["incident_id"] for i in await cap.registry()] == ["INC-2026-004"]


@pytest.mark.asyncio
async def test_execute_goes_through_workspace_exec_and_returns_evidence_verbatim(cap):
    evidence = await cap.execute("uv run pytest -q", "src/backend")
    assert (evidence.exit_code, evidence.stdout, evidence.stderr) == (3, "out", "err")
    name, args = cap._tool.calls[-1]
    assert name == "workspace_exec"
    assert args == {
        "user_id": "reg-user",
        "workspace_id": "macae-clone",
        "command": "uv run pytest -q",
        "path": "src/backend",
        "timeout": wc.EXEC_TIMEOUT_SECONDS,
    }
    await cap.execute("true", ".")
    assert cap._tool.calls[-1][1]["path"] == ""


@pytest.mark.asyncio
async def test_tool_error_is_a_capability_failure_not_evidence(cap):
    with pytest.raises(RuntimeError, match="Workspace not found"):
        await cap.execute("boom", ".")


def test_discover_finds_the_workspace_that_holds_the_registry(clone):
    """Cero configuración: el registro es el workspace que tiene docs/incidents."""
    cap = discover()

    assert cap is not None
    assert (cap.user_id, cap.workspace_id) == ("reg-user", "macae-clone")


def test_discover_returns_nothing_when_no_workspace_holds_a_registry(
    tmp_path, monkeypatch
):
    empty = tmp_path / "vacia"
    (empty / "otro-user" / "sin-registro").mkdir(parents=True)
    monkeypatch.setattr(ws_mod, "WORKSPACE_ROOT", empty)
    monkeypatch.setattr(wc, "WORKSPACE_ROOT", empty)

    assert discover() is None


def test_discover_refuses_to_guess_between_two_registries(clone, caplog):
    root = clone.parent.parent
    second = root / "otro-user" / "otro-clon"
    (second / "docs" / "incidents").mkdir(parents=True)
    (second / "docs" / "incidents" / "INC-2026-004.x.json").write_text(json.dumps(INC))

    with caplog.at_level("WARNING"):
        assert discover() is None

    assert "ambiguo" in caplog.text
    assert "otro-user/otro-clon" in caplog.text


@pytest.mark.asyncio
async def test_a_workspace_that_is_not_the_registry_is_read_as_is(cap, caplog):
    """Sólo el registro que ``discover()`` eligió se adelanta; cualquier otro
    workspace se lee tal cual, sin merge por debajo."""
    assert cap.owned is False

    with caplog.at_level("INFO"):
        await cap.registry()
        await cap.registry()
        await cap.registry()

    # Condición estable: se dice una vez, no en cada vuelta del reconciliador.
    assert caplog.text.count("se lee tal cual, sin adelantar") == 1
    assert [name for name, _ in cap._tool.calls] == []


@pytest.mark.asyncio
async def test_the_discovered_registry_is_fast_forwarded_before_reading(clone):
    cap = WorkspaceCapability(
        user_id="reg-user", workspace_id=clone.name, tool=FakeTool(), owned=True
    )

    assert cap.owned is True
    incidents = await cap.registry()

    name, args = cap._tool.calls[0]
    assert name == "workspace_exec"
    # En el sandbox: origin = share, upstream = el repositorio declarado. Se
    # adelanta desde upstream y se publica al share, en un solo comando de exec.
    # Primero a la punta del share (origin): un share recreado deja el sandbox
    # detrás y el push se rechaza (prod 2026-10-03, exit 1 "behind its remote").
    assert "git fetch --quiet origin && " in args["command"]
    assert 'git checkout --quiet -B "$b" "origin/$b" && ' in args["command"]
    assert args["command"].index("origin/$b") < args["command"].index(
        "git fetch --quiet upstream"
    )
    assert "git fetch --quiet upstream" in args["command"]
    assert "git merge --ff-only --quiet" in args["command"]
    # El receive-pack del share nace sin la configuración del cliente: la
    # confianza va en el comando del pack (INC-2026-013).
    assert (
        "git push --quiet --receive-pack='git -c safe.directory=* receive-pack' origin"
        in args["command"]
    )
    assert args["path"] == ""
    assert [i["incident_id"] for i in incidents] == ["INC-2026-004"]


class ShellTool:
    """Ejecuta el comando de verdad en un sandbox git real."""

    def __init__(self, cwd):
        self.cwd = cwd

    async def call_tool(self, tool_name, **kwargs):
        done = subprocess.run(
            ["bash", "-c", kwargs["command"]], cwd=self.cwd, capture_output=True
        )
        return json.dumps(
            {
                "status": "success",
                "action": tool_name,
                "details": {
                    "exit_code": done.returncode,
                    "stdout": done.stdout.decode(),
                    "stderr": done.stderr.decode(),
                },
            }
        )

    async def close(self):
        pass


def _run_git(cwd, *args):
    return (
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .strip()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("detached", [False, True])
async def test_the_fast_forward_never_discards_unpublished_sandbox_commits(
    clone, tmp_path, detached
):
    """Árbol limpio no basta: un commit que el share no tiene se perdería con
    ``checkout -B``. Se detecta la divergencia y no se resetea."""
    (clone / ".macae_workspace_meta.json").write_text(json.dumps({"branch": "main"}))
    upstream = tmp_path / "upstream"
    _run_git(tmp_path, "init", "-q", "-b", "main", str(upstream))
    _run_git(upstream, "commit", "-q", "--allow-empty", "-m", "base")
    share = tmp_path / "share"
    _run_git(tmp_path, "clone", "-q", str(upstream), str(share))
    sandbox = tmp_path / "sandbox"
    _run_git(tmp_path, "clone", "-q", str(share), str(sandbox))
    _run_git(sandbox, "remote", "add", "upstream", str(upstream))
    _run_git(sandbox, "commit", "-q", "--allow-empty", "-m", "local")
    local = _run_git(sandbox, "rev-parse", "HEAD")
    if detached:
        _run_git(sandbox, "checkout", "-q", "--detach")
        _run_git(sandbox, "branch", "-q", "-f", "main", "origin/main")
    cap = WorkspaceCapability(
        user_id="reg-user",
        workspace_id=clone.name,
        tool=ShellTool(sandbox),
        owned=True,
    )

    await cap.registry()

    assert _run_git(sandbox, "rev-parse", "HEAD") == local


@pytest.mark.asyncio
async def test_the_fast_forward_uses_the_branch_declared_at_mount_not_head(clone):
    """La rama viene del meta del workspace (intención al montar), no del HEAD
    circunstancial del sandbox."""
    (clone / ".macae_workspace_meta.json").write_text(
        json.dumps({"name": "x", "branch": "stable/v4-baseline"})
    )
    cap = WorkspaceCapability(
        user_id="reg-user", workspace_id=clone.name, tool=FakeTool(), owned=True
    )

    await cap.registry()

    _, args = cap._tool.calls[0]
    assert "b=stable/v4-baseline && " in args["command"]
    assert "rev-parse --abbrev-ref HEAD" not in args["command"]


def test_the_own_workspace_wins_over_any_other_registry(clone, caplog):
    root = clone.parent.parent
    own = root / "otro-user" / REGISTRY_WORKSPACE_ID
    (own / "docs" / "incidents").mkdir(parents=True)
    (own / "docs" / "incidents" / "INC-2026-004.x.json").write_text(json.dumps(INC))

    cap = discover()

    assert cap is not None
    assert (cap.user_id, cap.workspace_id) == ("otro-user", REGISTRY_WORKSPACE_ID)
    assert cap.owned is True


def test_one_registry_reachable_under_several_identities_is_not_ambiguous(
    clone, monkeypatch, caplog
):
    """El mismo clon enlazado desde varios ``user_id`` es UN registro.

    Medido 2026-09-24: tres alias del mismo directorio (el usuario de la UI
    local, el sample_user de dev y el oid de prod) se contaban como tres
    registros, `discover` se declaraba ambiguo y el reconciliador no originaba
    trabajo nunca.
    """
    monkeypatch.delenv("INCIDENT_REGISTRY_USER_ID", raising=False)
    root = clone.parent.parent
    for alias in ("d1f2b268-d4a3-4db9-972b-bb7445ba2508", "zzz-last-user"):
        (root / alias).mkdir(parents=True, exist_ok=True)
        (root / alias / clone.name).symlink_to(clone, target_is_directory=True)

    cap = discover()

    assert cap is not None, "un registro con alias no puede ser ambiguo"
    assert cap.workspace_id == clone.name
    # Sin identidad declarada, la primera en orden: estable entre arranques.
    assert cap.user_id == "d1f2b268-d4a3-4db9-972b-bb7445ba2508"
    assert "ambiguo" not in caplog.text


def test_the_declared_identity_decides_which_alias_works(clone, monkeypatch):
    """``INCIDENT_REGISTRY_USER_ID`` desempata entre alias del mismo registro:
    el reconciliador no tiene identidad propia y llama a ca-mcp con esta."""
    root = clone.parent.parent
    alias = root / "d1f2b268-d4a3-4db9-972b-bb7445ba2508"
    alias.mkdir(parents=True, exist_ok=True)
    (alias / clone.name).symlink_to(clone, target_is_directory=True)
    monkeypatch.setenv("INCIDENT_REGISTRY_USER_ID", "reg-user")

    cap = discover()

    assert cap is not None
    assert (cap.user_id, cap.workspace_id) == ("reg-user", clone.name)


def test_two_different_registries_are_still_ambiguous(clone, monkeypatch, caplog):
    """La ambigüedad de verdad sigue deteniendo al reconciliador: dos clones
    DISTINTOS, cada uno con su propio ``docs/incidents``, no se adivinan."""
    monkeypatch.delenv("INCIDENT_REGISTRY_USER_ID", raising=False)
    root = clone.parent.parent
    other = root / "otro-user" / "otro-clon"
    (other / "docs" / "incidents").mkdir(parents=True)
    (other / "docs" / "incidents" / "INC-2026-004.x.json").write_text(json.dumps(INC))

    assert discover() is None
    assert "ambiguo" in caplog.text


@pytest.mark.asyncio
async def test_the_source_commit_is_read_with_the_share_trust_declared(
    cap, clone, monkeypatch
):
    """Sobre el share (SMB) git aborta por "dubious ownership" y ``source``
    quedaba vacío: la evidencia no decía contra qué commit corrió la sonda. La
    condición no es reproducible portablemente (haría falta otro uid; el
    interruptor interno de git lo ignora la 2.55 del runner), así que se
    verifica el contrato: ``_head`` declara ``safe.directory`` para el árbol y
    devuelve el commit real."""
    for args in (
        ["config", "user.email", "reg@local"],
        ["config", "user.name", "reg"],
        ["add", "-A"],
        ["commit", "-q", "-m", "registro"],
    ):
        subprocess.run(["git", *args], cwd=clone, check=True, capture_output=True)
    seen = []
    real = subprocess.run

    def spy(cmd, *a, **k):
        if cmd and cmd[0] == "git":
            seen.append(list(cmd))
        return real(cmd, *a, **k)

    monkeypatch.setattr(wc.subprocess, "run", spy)

    await cap.registry()

    head_calls = [c for c in seen if "rev-parse" in c and "HEAD" in c]
    assert head_calls, "no se leyó HEAD"
    for cmd in head_calls:
        trusts = {cmd[i + 1] for i, tok in enumerate(cmd) if tok == "-c"}
        assert f"safe.directory={clone}" in trusts, cmd
    assert len(cap.source) == 40


# ── desempate global entre registros DISTINTOS ───────────────────────────────
# Medido en local 2026-09-27: dos clones DISTINTOS del repo (el sample_user de
# dev y el oid real, cada uno con su docs/incidents) dejaban el descubrimiento
# ambiguo AUNQUE la identidad de trabajo estuviera declarada, que es la función
# que su propio docstring promete. No se colapsan por ``origin``: pueden estar
# en ramas o commits distintos y eso escondería una divergencia real.


def _second_registry(root, user="otro-user", name="otro-clon"):
    other = root / user / name
    (other / "docs" / "incidents").mkdir(parents=True)
    (other / "docs" / "incidents" / "INC-2026-004.x.json").write_text(json.dumps(INC))
    subprocess.run(["git", "init", "-q", str(other)], check=True)
    return other


def test_the_declared_identity_breaks_a_tie_between_different_registries(
    clone, monkeypatch, caplog
):
    root = clone.parent.parent
    _second_registry(root)
    monkeypatch.setenv("INCIDENT_REGISTRY_USER_ID", "reg-user")

    cap = discover()

    assert cap is not None
    assert (cap.user_id, cap.workspace_id) == ("reg-user", clone.name)
    assert "ambiguo" not in caplog.text


def test_the_canonical_name_wins_before_the_declared_identity(clone, monkeypatch):
    """El nombre canónico es el PRIMER criterio: la identidad declarada sólo
    desempata lo que queda después de aplicarlo."""
    root = clone.parent.parent
    canonico = root / "otro-user" / REGISTRY_WORKSPACE_ID
    (canonico / "docs" / "incidents").mkdir(parents=True)
    (canonico / "docs" / "incidents" / "INC-2026-004.x.json").write_text(
        json.dumps(INC)
    )
    monkeypatch.setenv("INCIDENT_REGISTRY_USER_ID", "reg-user")

    cap = discover()

    assert cap is not None
    assert (cap.user_id, cap.workspace_id) == ("otro-user", REGISTRY_WORKSPACE_ID)


def test_the_declared_identity_also_breaks_a_tie_between_canonical_clones(
    clone, monkeypatch
):
    root = clone.parent.parent
    for user in ("aaa-user", "reg-user"):
        ws = root / user / REGISTRY_WORKSPACE_ID
        (ws / "docs" / "incidents").mkdir(parents=True)
        (ws / "docs" / "incidents" / "INC-2026-004.x.json").write_text(json.dumps(INC))
    monkeypatch.setenv("INCIDENT_REGISTRY_USER_ID", "reg-user")

    cap = discover()

    assert cap is not None
    assert (cap.user_id, cap.workspace_id) == ("reg-user", REGISTRY_WORKSPACE_ID)


def test_a_declared_identity_that_matches_nothing_leaves_it_ambiguous(
    clone, monkeypatch, caplog
):
    """No se cae al primero por tener la variable puesta: si no coincide con
    ningún candidato sigue siendo ambiguo, y se dice por qué."""
    root = clone.parent.parent
    _second_registry(root)
    monkeypatch.setenv("INCIDENT_REGISTRY_USER_ID", "nadie")

    with caplog.at_level("INFO"):
        assert discover() is None

    assert "no está entre los candidatos" in caplog.text
    assert "ambiguo" in caplog.text
