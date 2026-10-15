"""
Tests for workspace MCP service behaviors.
"""

import json
import subprocess
from json import JSONDecodeError, loads
from pathlib import Path

import pytest

from core.factory import Domain
from services import workspace_service


@pytest.fixture
def workspace_tools(mock_mcp_server):
    """Register workspace tools and return them by function name."""
    service = workspace_service.WorkspaceToolService()
    service.register_tools(mock_mcp_server)

    return {
        tool["func"].__name__: tool["func"] for tool in mock_mcp_server.tools
    }, mock_mcp_server


@pytest.fixture
def workspace_root(tmp_path, monkeypatch):
    """Point workspace resolution at a temporary root."""
    root = (tmp_path / "workspaces").resolve()
    root.mkdir()
    monkeypatch.setattr(workspace_service, "WORKSPACE_ROOT", root)
    # El sandbox (computación) vive aparte del share (durabilidad).
    sandboxes = (tmp_path / "sandboxes").resolve()
    monkeypatch.setattr(workspace_service, "SANDBOX_ROOT", sandboxes)
    return root


def _make_workspace(root, user_id="user-1", workspace_id="workspace-1"):
    workspace = root / user_id / workspace_id
    workspace.mkdir(parents=True)
    return workspace, user_id, workspace_id


def _init_git_repo(path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)


class TestWorkspaceToolService:
    """Test cases for workspace tools."""

    def test_register_tools(self, workspace_tools):
        """Test tool registration."""
        tools, mock_mcp_server = workspace_tools
        service = workspace_service.WorkspaceToolService()

        assert len(mock_mcp_server.tools) == service.tool_count
        assert "workspace_git_status" in tools
        assert "workspace_write_file" in tools
        for tool in mock_mcp_server.tools:
            assert Domain.WORKSPACE.value in tool["tags"]

    def test_workspace_git_status_returns_error_on_git_failure(
        self, workspace_root, workspace_tools, monkeypatch
    ):
        """Test git status surfaces git command failures."""
        tools, _ = workspace_tools
        _, user_id, workspace_id = _make_workspace(workspace_root)

        def mock_git(_ws, *args, trust=()):
            # La materialización del sandbox también pasa por _git; sólo el
            # `status` de la tool tiene que fallar. Un clone real deja el
            # repositorio en el destino (el último argumento).
            if args and args[0] == "clone":
                (Path(args[-1]) / ".git").mkdir(parents=True, exist_ok=True)
            if args[:2] == ("status", "--short"):
                return subprocess.CompletedProcess(
                    ["git", *args], 128, stdout=b"", stderr=b"fatal: not a git repository"
                )
            out = b"main\n" if "symbolic-ref" in args else b""
            return subprocess.CompletedProcess(["git", *args], 0, stdout=out, stderr=b"")

        monkeypatch.setattr(workspace_service, "_git", mock_git)

        result = tools["workspace_git_status"](user_id, workspace_id)

        payload = loads(result)
        assert payload["status"] == "error"
        assert payload["action"] == "workspace_git_status"
        assert "git status failed: fatal: not a git repository" in payload["summary"]

    def test_workspace_write_file_rejects_non_git_workspace(
        self, workspace_root, workspace_tools
    ):
        """Test writes are rejected before mutating a non-git workspace."""
        tools, _ = workspace_tools
        workspace, user_id, workspace_id = _make_workspace(workspace_root)

        result = tools["workspace_write_file"](
            user_id, workspace_id, "notes.txt", "hello"
        )

        assert "Workspace is not a git repository" in result
        assert not (workspace / "notes.txt").exists()

    def test_workspace_write_file_rejects_path_outside_workspace(
        self, workspace_root, workspace_tools
    ):
        """Test writes cannot escape the workspace root."""
        tools, _ = workspace_tools
        workspace, user_id, workspace_id = _make_workspace(workspace_root)
        _init_git_repo(workspace)

        result = tools["workspace_write_file"](
            user_id, workspace_id, "../escape.txt", "hello"
        )

        assert "Path outside workspace." in result
        assert not (workspace.parent / "escape.txt").exists()

    def test_workspace_write_file_rejects_content_over_size_limit(
        self, workspace_root, workspace_tools
    ):
        """Test writes over the max file size are rejected."""
        tools, _ = workspace_tools
        workspace, user_id, workspace_id = _make_workspace(workspace_root)
        _init_git_repo(workspace)
        content = "a" * (workspace_service.MAX_FILE_BYTES + 1)

        result = tools["workspace_write_file"](
            user_id, workspace_id, "large.txt", content
        )

        assert (
            f"File too large ({len(content)} bytes). Max is "
            f"{workspace_service.MAX_FILE_BYTES} bytes."
        ) in result
        assert not (workspace / "large.txt").exists()

    def test_workspace_write_file_writes_and_commits(
        self, workspace_root, workspace_tools
    ):
        """Test successful writes are committed immediately."""
        tools, _ = workspace_tools
        workspace, user_id, workspace_id = _make_workspace(workspace_root)
        _init_git_repo(workspace)

        result = tools["workspace_write_file"](
            user_id, workspace_id, "notes.txt", "hello", "agent: write notes.txt"
        )

        try:
            payload = loads(result)
        except JSONDecodeError as exc:
            pytest.fail(f"Expected a JSON success response, got: {result} ({exc})")
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=workspace,
            check=True,
            capture_output=True,
            text=True,
        )
        commit_message = subprocess.run(
            ["git", "log", "-1", "--pretty=%s"],
            cwd=workspace,
            check=True,
            capture_output=True,
            text=True,
        )

        assert payload["status"] == "success"
        assert payload["action"] == "workspace_write_file"
        details = payload["details"]
        assert (details["path"], details["bytes"]) == ("notes.txt", 5)
        # Se commitea en el sandbox y se PUBLICA al share: lo que el usuario ve.
        assert details["committed"] is True and details["published"] is True
        assert details["publish_detail"].startswith("published to '")
        assert payload["summary"].startswith(
            "Wrote 5 bytes to 'notes.txt'; published to '")
        assert (workspace / "notes.txt").read_text(encoding="utf-8") == "hello"
        assert status.stdout.strip() == ""
        assert commit_message.stdout.strip() == "agent: write notes.txt"


# ── dueño ajeno en el share: el pre-flight es parte del contrato ─────────────
# Sobre Azure Files/SMB el árbol no pertenece al uid del proceso y git rechaza
# TODA operación con "detected dubious ownership" (medido en prod). Esa
# condición no se puede reproducir portablemente en un test: haría falta otro
# uid, y el interruptor GIT_TEST_ASSUME_DIFFERENT_OWNER es interno de git y la
# 2.55 del runner lo ignora (medido en Actions). Saltear el test cuando git no
# lo honra sería un guardián alrededor de basura. Lo determinista, y ajeno a la
# versión de git, es el CONTRATO: cada git que corre sobre el share declara
# safe.directory para el share y, en clone/fetch/push, también para su .git
# (git valida el origen por su gitdir); y el entorno de exec declara la
# confianza del sandbox para los git que corra el propio agente.


class TestOwnershipPreflight:
    def _spy(self, monkeypatch):
        seen = []
        real = subprocess.run

        def run(cmd, *a, **k):
            if cmd and cmd[0] == "git":
                seen.append((list(cmd), str(k.get("cwd") or "")))
            return real(cmd, *a, **k)

        monkeypatch.setattr(workspace_service.subprocess, "run", run)
        return seen

    @staticmethod
    def _trusts(cmd):
        return {cmd[i + 1] for i, tok in enumerate(cmd) if tok == "-c"}

    def test_every_git_call_on_the_share_declares_its_trust(
        self, workspace_tools, workspace_root, monkeypatch
    ):
        tools, _ = workspace_tools
        share, uid, wid = _make_workspace(workspace_root)
        _init_git_repo(share)
        seen = self._spy(monkeypatch)

        tools["workspace_git_status"](uid, wid)  # materializa (clone) y consulta

        on_share = [cmd for cmd, cwd in seen if cwd == str(share)]
        assert on_share, "ninguna llamada corrió sobre el share"
        for cmd in on_share:
            assert f"safe.directory={share}" in self._trusts(cmd), cmd

    def test_clone_fetch_and_push_also_trust_the_shares_gitdir(
        self, workspace_tools, workspace_root, monkeypatch
    ):
        tools, _ = workspace_tools
        share, uid, wid = _make_workspace(workspace_root)
        _init_git_repo(share)
        (share / "a.txt").write_text("1")
        _commit(share, "init")
        seen = self._spy(monkeypatch)

        tools["workspace_git_status"](uid, wid)  # clone
        tools["workspace_write_file"](uid, wid, "b.txt", "2")  # push
        tools["workspace_git_status"](uid, wid)  # sandbox limpio → fetch

        for op in ("clone", "fetch", "push"):
            cmds = [cmd for cmd, _ in seen if op in cmd]
            assert cmds, f"no hubo {op}"
            for cmd in cmds:
                trusts = self._trusts(cmd)
                assert f"safe.directory={share}" in trusts, cmd
                assert f"safe.directory={share / '.git'}" in trusts, cmd

    def test_exec_carries_the_trust_so_the_agent_can_run_git_itself(self, workspace_root):
        workspace, _, _ = _make_workspace(workspace_root)

        env = workspace_service._child_env(workspace)

        assert env["GIT_CONFIG_COUNT"] == "1"
        assert env["GIT_CONFIG_KEY_0"] == "safe.directory"
        assert env["GIT_CONFIG_VALUE_0"] == str(workspace)
        assert "GIT_CONFIG_COUNT" not in workspace_service._child_env()


# ── la arquitectura: share = durabilidad, sandbox = computación ──────────────
# Medido en prod: Azure Files no admite enlaces simbólicos (ningún venv puede
# existir ahí), git lo rechaza por dueño ajeno y cada I/O paga red. Todo eso es
# computación y va a un clon local; el share guarda el repo y lo que el usuario
# ve. Estos tests prueban cada garantía del diagrama, sobre git real.


def _commit(path, msg):
    for a in (
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["add", "-A"],
        ["commit", "-q", "--allow-empty", "-m", msg],
    ):
        subprocess.run(["git", *a], cwd=path, check=True, capture_output=True)


def _git_out(path, *args):
    return subprocess.run(
        ["git", *args], cwd=path, check=True, capture_output=True, text=True
    ).stdout.strip()


class TestSandboxArchitecture:
    def _share(self, root, **kw):
        share, uid, wid = _make_workspace(root, **kw)
        _init_git_repo(share)
        (share / "README.md").write_text("durable\n")
        _commit(share, "init")
        return share, uid, wid

    def test_exec_runs_in_a_local_sandbox_where_a_venv_can_be_created(
        self, workspace_tools, workspace_root
    ):
        """Lo que en el share era imposible: un venv necesita symlinks."""
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)

        out = loads(tools["workspace_exec"](
            uid, wid, "pwd && python3 -m venv .venv && ls .venv/bin/python"))

        assert out["details"]["exit_code"] == 0, out["details"]
        cwd = out["details"]["stdout"].splitlines()[0]
        assert cwd.startswith(str(workspace_service.SANDBOX_ROOT))
        assert not str(cwd).startswith(str(workspace_root))
        assert (workspace_service._sandbox_path(uid, wid)
                / ".venv" / "bin" / "python").exists()
        assert not (share / ".venv").exists(), "la computación no toca el share"

    def test_uncommitted_exec_output_is_ephemeral_until_published(
        self, workspace_tools, workspace_root
    ):
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)

        assert loads(tools["workspace_exec"](uid, wid, "echo hola > generado.txt"))[
            "details"]["exit_code"] == 0
        assert not (share / "generado.txt").exists()

        pub = loads(tools["workspace_publish"](uid, wid, "guardar lo generado"))

        assert pub["details"]["published"] is True
        assert (share / "generado.txt").read_text() == "hola\n"
        assert _git_out(share, "log", "-1", "--pretty=%s") == "guardar lo generado"

    def test_an_interrupted_clone_is_discarded_and_the_sandbox_rematerialized(
        self, workspace_tools, workspace_root
    ):
        """Medido 2026-10-10: un clone cortado deja ``.git`` con
        ``HEAD -> refs/heads/.invalid`` y el sandbox quedaba vacío para siempre.
        Un resto así se descarta, lo mismo que un temporal de otro proceso, y
        lo que se promueve ya viene configurado (identidad antes del rename)."""
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)
        sandbox = workspace_service._sandbox_path(uid, wid)
        (sandbox / ".git").mkdir(parents=True)
        (sandbox / ".git" / "HEAD").write_text("ref: refs/heads/.invalid\n")
        stale = sandbox.parent / f".materializing-{wid}-999999"
        stale.mkdir(parents=True)

        out = loads(tools["workspace_list_entries"](uid, wid))

        names = [e["name"] for e in out["details"]["entries"]]
        assert "README.md" in names, out
        assert _git_out(sandbox, "rev-parse", "--verify", "HEAD")
        assert _git_out(sandbox, "config", "user.name") == workspace_service._GIT_IDENTITY[0]
        assert not stale.exists()
        assert not list(sandbox.parent.glob(f".materializing-{wid}-*"))

    def test_a_live_materializers_clone_in_progress_is_not_removed_by_cleanup(
        self, workspace_tools, workspace_root
    ):
        """Medido 2026-10-10: con ``SANDBOX_ROOT`` compartido dos procesos pueden
        materializar a la vez. El que entra a limpiar restos no debe borrar el
        clone en curso de otro proceso vivo; sólo descarta los huérfanos."""
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)
        sandbox = workspace_service._sandbox_path(uid, wid)
        sandbox.parent.mkdir(parents=True, exist_ok=True)
        alive = subprocess.Popen(["sleep", "30"])
        try:
            in_progress = sandbox.parent / f".materializing-{wid}-{alive.pid}"
            in_progress.mkdir(parents=True)
            (in_progress / "clone-en-curso").write_text("otro proceso vivo\n")
            orphan = sandbox.parent / f".materializing-{wid}-999999"
            orphan.mkdir(parents=True)

            out = loads(tools["workspace_list_entries"](uid, wid))

            assert out["status"] != "error", out
            assert in_progress.exists(), "no se borra el clone de un proceso vivo"
            assert (in_progress / "clone-en-curso").read_text() == "otro proceso vivo\n"
            assert not orphan.exists(), "los temporales huérfanos sí se descartan"
        finally:
            alive.terminate()
            alive.wait()

    def test_a_failed_clone_leaves_neither_sandbox_nor_staging(
        self, workspace_tools, workspace_root, monkeypatch
    ):
        tools, _ = workspace_tools
        _, uid, wid = self._share(workspace_root)
        sandbox = workspace_service._sandbox_path(uid, wid)
        real_git = workspace_service._git

        def failing_clone(ws, *args, **kw):
            if args and args[0] == "clone":
                return subprocess.CompletedProcess(
                    ["git", *args], 128, stdout=b"", stderr=b"fatal: clone cortado"
                )
            return real_git(ws, *args, **kw)

        monkeypatch.setattr(workspace_service, "_git", failing_clone)

        out = loads(tools["workspace_list_entries"](uid, wid))

        assert out["status"] == "error" and "clone cortado" in out["summary"]
        assert not sandbox.exists()
        assert not list(sandbox.parent.glob(f".materializing-{wid}-*"))

    def test_write_tools_publish_and_the_user_sees_it_in_the_durable_tree(
        self, workspace_tools, workspace_root
    ):
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)

        r = loads(tools["workspace_create_file"](uid, wid, "src/x.py", "print(1)\n"))

        assert r["details"]["published"] is True
        assert (share / "src" / "x.py").read_text() == "print(1)\n"
        assert _git_out(share, "status", "--short") == ""

    def test_a_write_still_publishes_when_the_durable_tree_advanced_meanwhile(
        self, workspace_tools, workspace_root
    ):
        """Medido 2026-10-14 en local: el share avanzó (ritual post-merge)
        después de materializar el sandbox; el agente escribió y commiteó, el
        push fue rechazado (non-fast-forward) y el archivo nunca llegó al
        explorador. Antes de publicar, el sandbox se pone al día con el share
        y el commit del agente queda encima de lo nuevo."""
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)
        tools["workspace_git_status"](uid, wid)  # materializa el sandbox
        (share / "OTHER.md").write_text("otro escritor\n")
        _commit(share, "advance the durable tree")

        r = loads(tools["workspace_write_file"](uid, wid, "a.txt", "x"))

        assert r["details"]["published"] is True, r["details"]
        assert (share / "a.txt").read_text() == "x"
        assert (share / "OTHER.md").read_text() == "otro escritor\n"
        assert _git_out(share, "status", "--short") == ""
        assert _git_out(share, "log", "--format=%s", "-2").splitlines()[1] == (
            "advance the durable tree"
        )

    def test_publish_is_refused_when_the_durable_tree_has_unsaved_edits(
        self, workspace_tools, workspace_root
    ):
        """Dos escritores sin acuerdo no se resuelven a ciegas: el usuario editó
        en Monaco sin commitear, el push se rechaza y se reporta; su edición
        queda intacta y el trabajo del agente queda commiteado en el sandbox."""
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)
        tools["workspace_git_status"](uid, wid)  # materializa
        (share / "README.md").write_text("editado en Monaco\n")

        r = loads(tools["workspace_write_file"](uid, wid, "a.txt", "x"))

        assert r["details"]["committed"] is True
        assert r["details"]["published"] is False
        assert not (share / "a.txt").exists()
        assert (share / "README.md").read_text() == "editado en Monaco\n"
        sandbox = workspace_service._sandbox_path(uid, wid)
        assert (sandbox / "a.txt").read_text() == "x"
        assert _git_out(sandbox, "log", "-1", "--pretty=%s") == "agent: write a.txt"

    def test_user_commits_on_the_durable_tree_reach_a_clean_sandbox(
        self, workspace_tools, workspace_root
    ):
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)
        tools["workspace_git_status"](uid, wid)  # materializa
        (share / "nuevo.txt").write_text("del usuario\n")
        _commit(share, "usuario")

        r = loads(tools["workspace_read_file"](uid, wid, "nuevo.txt"))

        assert r["status"] == "success", r
        assert "del usuario" in r["details"]["content"]

    def test_a_sandbox_with_local_work_is_never_overwritten(
        self, workspace_tools, workspace_root
    ):
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)
        tools["workspace_exec"](uid, wid, "echo local > local.txt")  # sandbox sucio
        (share / "nuevo2.txt").write_text("del usuario\n")
        _commit(share, "usuario")

        r = tools["workspace_read_file"](uid, wid, "nuevo2.txt")

        assert loads(r)["status"] == "error"  # no se adelantó: no se pisa trabajo local
        assert (workspace_service._sandbox_path(uid, wid) / "local.txt").exists()

    def test_upstream_is_the_repository_declared_at_mount_not_the_shares_origin(
        self, workspace_tools, workspace_root
    ):
        """El share enlazado puede apuntar a OTRO remoto (aquí microsoft); el
        workspace se montó desde macae-labs y eso es lo que dice su meta."""
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/microsoft/otro.git"],
            cwd=share, check=True, capture_output=True,
        )
        (share / workspace_service._META_FILE).write_text(
            json.dumps({"name": "w", "repo_url": "https://github.com/macae-labs/repo.git"})
        )

        tools["workspace_git_status"](uid, wid)  # materializa

        sandbox = workspace_service._sandbox_path(uid, wid)
        assert _git_out(sandbox, "remote", "get-url", "origin") == str(share)
        assert _git_out(sandbox, "remote", "get-url",
                        "upstream") == "https://github.com/macae-labs/repo.git"
        assert _git_out(share, "config", "receive.denyCurrentBranch") == "updateInstead"

    def test_a_workspace_without_a_declared_repository_gets_no_upstream(
        self, workspace_tools, workspace_root
    ):
        """Aunque el share tenga origin: sin repo declarado no hay de dónde
        adelantar, y heredar el origin del share inventaría una intención."""
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/microsoft/otro.git"],
            cwd=share, check=True, capture_output=True,
        )

        tools["workspace_git_status"](uid, wid)

        sandbox = workspace_service._sandbox_path(uid, wid)
        assert subprocess.run(
            ["git", "remote", "get-url", "upstream"], cwd=sandbox, capture_output=True
        ).returncode != 0

    def test_the_sandbox_is_materialized_and_published_on_the_declared_branch(
        self, workspace_tools, workspace_root
    ):
        """El share puede tener checkout otra rama; la declarada al montar manda,
        en el clon del sandbox y en el destino del publish."""
        tools, _ = workspace_tools
        share, uid, wid = self._share(workspace_root)
        subprocess.run(["git", "branch", "stable/v4-baseline"],
                       cwd=share, check=True, capture_output=True)
        (share / workspace_service._META_FILE).write_text(
            json.dumps({"name": "w", "branch": "stable/v4-baseline"})
        )
        master_before = _git_out(share, "rev-parse", "master")

        r = loads(tools["workspace_write_file"](uid, wid, "en_rama.txt", "x"))

        sandbox = workspace_service._sandbox_path(uid, wid)
        assert _git_out(sandbox, "rev-parse", "--abbrev-ref",
                        "HEAD") == "stable/v4-baseline"
        assert r["details"]["published"] is True
        assert _git_out(share, "rev-parse",
                        "stable/v4-baseline") == _git_out(sandbox, "rev-parse", "HEAD")
        # la otra rama, intacta
        assert _git_out(share, "rev-parse", "master") == master_before

    def test_two_users_with_the_same_workspace_name_get_separate_sandboxes(
        self, workspace_tools, workspace_root
    ):
        tools, _ = workspace_tools
        _, u1, w = self._share(workspace_root, user_id="ana", workspace_id="repo")
        _, u2, _ = self._share(workspace_root, user_id="beto", workspace_id="repo")
        tools["workspace_exec"](u1, w, "echo ana > quien.txt")

        r = tools["workspace_read_file"](u2, w, "quien.txt")

        assert loads(r)["status"] == "error"
        assert workspace_service._sandbox_path(
            u1, w) != workspace_service._sandbox_path(u2, w)
