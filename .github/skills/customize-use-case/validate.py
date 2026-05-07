#!/usr/bin/env python3
"""MACE adapter-skill validator."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_NAME = Path(__file__).resolve().parent.name

DEFAULT_TEAM_FILES = {
    "hr.json",
    "marketing.json",
    "retail.json",
    "rfp_analysis_team.json",
    "contract_compliance_team.json",
}
RESERVED_TEAM_IDS = {
    "team-1",
    "team-2",
    "team-3",
    "team-clm-1",
    "team-compliance-1",
}
RESERVED_TEAM_NAMES = {
    "Human Resources Team",
    "Product Marketing Team",
    "Retail Customer Success Team",
    "RFP Team",
    "Contract Compliance Review Team",
}
TEAM_TOP_LEVEL_REQUIRED = {
    "id",
    "team_id",
    "name",
    "status",
    "created",
    "created_by",
    "deployment_name",
    "agents",
    "description",
    "logo",
    "plan",
    "starting_tasks",
}
AGENT_REQUIRED = {
    "input_key",
    "type",
    "name",
    "icon",
    "deployment_name",
    "system_message",
    "description",
    "use_rag",
    "use_mcp",
    "use_bing",
    "use_reasoning",
    "index_name",
    "coding_tools",
}
TASK_REQUIRED = {"id", "name", "prompt", "created", "creator", "logo"}


@dataclass
class Result:
    name: str
    status: str
    details: str
    remediation: str = ""

    @property
    def failed(self) -> bool:
        return self.status == "fail"

    def emit(self) -> None:
        marker = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}[self.status]
        print(f"[{marker}] {self.name}: {self.details}")
        sys.stderr.write(
            json.dumps(
                {
                    "name": self.name,
                    "status": self.status,
                    "details": self.details,
                    "remediation": self.remediation,
                },
                sort_keys=True,
            )
            + "\n"
        )


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> tuple[dict | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        return None, f"{rel(path)}: invalid JSON at line {exc.lineno}: {exc.msg}"
    except OSError as exc:
        return None, f"{rel(path)}: cannot read file: {exc}"
    if not isinstance(data, dict):
        return None, f"{rel(path)}: root must be a JSON object"
    return data, None


def is_generated_team(path: Path) -> bool:
    if path.match("*/data/industry_packs/*/team_config.json"):
        return True
    if path.parent == REPO_ROOT / "data" / "agent_teams":
        return path.name not in DEFAULT_TEAM_FILES
    return False


def validate_generated_team(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    missing = sorted(TEAM_TOP_LEVEL_REQUIRED - data.keys())
    if missing:
        errors.append(f"{rel(path)} missing top-level keys {missing}")

    team_id = str(data.get("team_id", ""))
    name = str(data.get("name", ""))
    if team_id in RESERVED_TEAM_IDS:
        errors.append(f"{rel(path)} reuses reserved team_id {team_id}")
    if name in RESERVED_TEAM_NAMES:
        errors.append(f"{rel(path)} reuses reserved team name {name}")

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        errors.append(f"{rel(path)} agents must be a non-empty array")
        agents = []
    if len(agents) > 6:
        errors.append(f"{rel(path)} has {len(agents)} agents; frontend limit is 6")

    needs_proxy = False
    seen_names: set[str] = set()
    for index, agent in enumerate(agents, start=1):
        if not isinstance(agent, dict):
            errors.append(f"{rel(path)} agent {index} must be an object")
            continue
        missing_agent = sorted(AGENT_REQUIRED - agent.keys())
        if missing_agent:
            errors.append(f"{rel(path)} agent {index} missing keys {missing_agent}")
        agent_name = str(agent.get("name", ""))
        if agent_name in seen_names:
            errors.append(f"{rel(path)} duplicate agent name {agent_name}")
        seen_names.add(agent_name)
        if agent.get("use_rag") is True or agent.get("use_mcp") is True:
            needs_proxy = True
        if agent.get("use_rag") is True and not agent.get("index_name"):
            errors.append(f"{rel(path)} RAG agent {agent_name} needs index_name")
        if agent.get("use_reasoning") is True and agent.get("deployment_name") != "o4-mini":
            errors.append(f"{rel(path)} reasoning agent {agent_name} should use o4-mini")

    if needs_proxy:
        final_name = agents[-1].get("name") if agents and isinstance(agents[-1], dict) else ""
        if final_name != "ProxyAgent":
            errors.append(f"{rel(path)} RAG/MCP teams must end with ProxyAgent")

    tasks = data.get("starting_tasks")
    if not isinstance(tasks, list) or not tasks:
        errors.append(f"{rel(path)} starting_tasks must be a non-empty array")
        tasks = []
    for index, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            errors.append(f"{rel(path)} starting task {index} must be an object")
            continue
        missing_task = sorted(TASK_REQUIRED - task.keys())
        if missing_task:
            errors.append(f"{rel(path)} starting task {index} missing keys {missing_task}")

    return errors


def check_environment() -> Result:
    if sys.version_info < (3, 10):
        return Result(
            "environment",
            "fail",
            f"python {sys.version.split()[0]} is too old",
            "Use Python 3.10 or newer.",
        )
    if not (REPO_ROOT / "data" / "agent_teams").is_dir():
        return Result("environment", "fail", "data/agent_teams missing", "Run from the MACE repo root.")
    return Result("environment", "pass", f"repo={REPO_ROOT}, python={sys.version.split()[0]}")


def check_team_json() -> Result:
    paths = sorted((REPO_ROOT / "data" / "agent_teams").glob("*.json"))
    paths += sorted((REPO_ROOT / "data" / "industry_packs").glob("*/team_config.json"))
    if not paths:
        return Result("team_json", "fail", "no team JSON files found", "Restore data/agent_teams/*.json.")

    errors: list[str] = []
    generated_count = 0
    for path in paths:
        data, error = load_json(path)
        if error:
            errors.append(error)
            continue
        if data is None:
            continue
        if "name" not in data or "status" not in data:
            errors.append(f"{rel(path)} missing backend-required name/status")
        if "agents" not in data or not isinstance(data.get("agents"), list) or not data.get("agents"):
            errors.append(f"{rel(path)} missing non-empty agents array")
        if "starting_tasks" not in data or not isinstance(data.get("starting_tasks"), list) or not data.get("starting_tasks"):
            errors.append(f"{rel(path)} missing non-empty starting_tasks array")
        if is_generated_team(path):
            generated_count += 1
            errors.extend(validate_generated_team(path, data))

    if errors:
        return Result("team_json", "fail", "; ".join(errors), "Fix generated team JSON before upload.")
    return Result("team_json", "pass", f"{len(paths)} team files parsed; {generated_count} generated team files enforced")


def check_generated_artifacts() -> Result:
    errors: list[str] = []
    docs_root = REPO_ROOT / "docs" / "adaptations"
    if docs_root.is_dir():
        for folder in sorted(p for p in docs_root.iterdir() if p.is_dir()):
            for required in ["README.md", "SCHEMA_MAPPING.md", "DATA_SWAP_GUIDE.md", "ACTIVATION_HANDOFF.md"]:
                if not (folder / required).is_file():
                    errors.append(f"{rel(folder)} missing {required}")

    packs_root = REPO_ROOT / "data" / "industry_packs"
    if packs_root.is_dir():
        for folder in sorted(p for p in packs_root.iterdir() if p.is_dir()):
            readme = folder / "README.md"
            if not readme.is_file():
                errors.append(f"{rel(folder)} missing README.md with runtime promotion guidance")
                continue
            text = readme.read_text(encoding="utf-8", errors="replace")
            if "data/agent_teams" not in text or "data/datasets" not in text:
                errors.append(f"{rel(readme)} must explain promotion to data/agent_teams and data/datasets")

    if errors:
        return Result("generated_artifacts", "fail", "; ".join(errors), "Complete adaptation docs and runtime-path guidance.")
    return Result("generated_artifacts", "pass", "generated docs/industry pack structure is complete or absent")


def require_contains(path: Path, needles: list[str], errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"{rel(path)} missing")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    for needle in needles:
        if needle not in text:
            errors.append(f"{rel(path)} missing expected token {needle!r}")


def check_ui_contract() -> Result:
    errors: list[str] = []
    require_contains(
        REPO_ROOT / "src" / "App" / "src" / "models" / "Team.tsx",
        ["interface TeamConfig", "team_id", "starting_tasks", "agents"],
        errors,
    )
    require_contains(
        REPO_ROOT / "src" / "App" / "src" / "components" / "common" / "TeamSelector.tsx",
        ["uploadCustomTeam", "team-1", "team-compliance-1", "more than 6 agents"],
        errors,
    )
    require_contains(
        REPO_ROOT / "src" / "App" / "src" / "store" / "TeamService.tsx",
        ["upload_team_config", "getUserTeams", "selectTeam"],
        errors,
    )
    require_contains(
        REPO_ROOT / "src" / "App" / "src" / "components" / "content" / "HomeInput.tsx",
        ["starting_tasks", "prompt", "Quick tasks"],
        errors,
    )
    require_contains(
        REPO_ROOT / "src" / "backend" / "v4" / "common" / "services" / "team_service.py",
        ["validate_and_parse_team_config", "required_fields", "starting_tasks"],
        errors,
    )
    if errors:
        return Result("ui_contract", "fail", "; ".join(errors), "Restore frontend/backend team contract surfaces.")
    return Result("ui_contract", "pass", "team upload/display contract surfaces are present")


def check_compile() -> Result:
    targets = [
        Path(__file__),
        REPO_ROOT / "src" / "backend" / "common" / "models" / "messages_af.py",
        REPO_ROOT / "src" / "backend" / "v4" / "common" / "services" / "team_service.py",
    ]
    generated_services = sorted((REPO_ROOT / "src" / "mcp_server" / "services").glob("*_service.py"))
    targets.extend(generated_services)
    errors: list[str] = []
    for target in targets:
        if not target.is_file():
            continue
        try:
            source = target.read_text(encoding="utf-8")
            compile(source, str(target), "exec")
        except SyntaxError as exc:
            errors.append(f"{rel(target)}: line {exc.lineno}: {exc.msg}")
        except OSError as exc:
            errors.append(f"{rel(target)}: {exc}")
    if errors:
        return Result("compile", "fail", "; ".join(errors), "Fix Python syntax before deployment.")
    return Result("compile", "pass", f"compiled {len(targets)} Python files")


def run_shell(command: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def check_iac_build() -> Result:
    if shutil.which("az") is None:
        return Result("iac_build", "skip", "Azure CLI not found; skipped Bicep build")
    commands = [
        "az bicep build --file infra/main.bicep --stdout > /dev/null",
        "az bicep build --file infra/main_custom.bicep --stdout > /dev/null",
    ]
    errors: list[str] = []
    skipped: list[str] = []
    for command in commands:
        try:
            proc = run_shell(command, timeout=90)
        except subprocess.TimeoutExpired:
            skipped.append(f"{command}: timed out, likely AVM restore/network")
            continue
        output = (proc.stderr or proc.stdout or "").strip()
        if proc.returncode != 0:
            lower = output.lower()
            if "restore" in lower or "registry" in lower or "network" in lower or "timeout" in lower:
                skipped.append(f"{command}: {output[:180]}")
            else:
                errors.append(f"{command}: {output[:240]}")
    if errors:
        return Result("iac_build", "fail", "; ".join(errors), "Fix Bicep errors before azd provision/up.")
    if skipped:
        return Result("iac_build", "skip", "; ".join(skipped))
    return Result("iac_build", "pass", "Bicep templates compiled")


def check_tests() -> Result:
    if os.environ.get("MACE_VALIDATE_RUN_TESTS") != "1":
        return Result("tests", "skip", "set MACE_VALIDATE_RUN_TESTS=1 to run repository test suites")
    commands = [[sys.executable, "-m", "pytest"]]
    errors: list[str] = []
    for command in commands:
        try:
            proc = subprocess.run(command, cwd=str(REPO_ROOT), text=True, capture_output=True, timeout=600, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"{' '.join(command)}: {exc}")
            continue
        if proc.returncode != 0:
            errors.append(f"{' '.join(command)} exit={proc.returncode}: {(proc.stderr or proc.stdout)[:240]}")
    if errors:
        return Result("tests", "fail", "; ".join(errors), "Fix failing tests before deployment.")
    return Result("tests", "pass", "repository tests passed")


CHECKS: dict[str, Callable[[], Result]] = {
    "environment": check_environment,
    "team_json": check_team_json,
    "generated_artifacts": check_generated_artifacts,
    "ui_contract": check_ui_contract,
    "compile": check_compile,
    "iac_build": check_iac_build,
    "tests": check_tests,
}


def self_test() -> int:
    sample = {
        "id": "demo",
        "team_id": "team-demo",
        "name": "Demo Team",
        "status": "visible",
        "created": "",
        "created_by": "",
        "deployment_name": "gpt-4.1-mini",
        "agents": [
            {
                "input_key": "",
                "type": "",
                "name": "DemoDataAgent",
                "deployment_name": "gpt-4.1-mini",
                "icon": "",
                "system_message": "Demo only.",
                "description": "Demo data agent.",
                "use_rag": True,
                "use_mcp": False,
                "use_bing": False,
                "use_reasoning": False,
                "index_name": "macae-demo-data-index",
                "coding_tools": False,
            },
            {
                "input_key": "",
                "type": "",
                "name": "ProxyAgent",
                "deployment_name": "",
                "icon": "",
                "system_message": "",
                "description": "",
                "use_rag": False,
                "use_mcp": False,
                "use_bing": False,
                "use_reasoning": False,
                "index_name": "",
                "coding_tools": False,
            },
        ],
        "protected": False,
        "description": "Demo.",
        "logo": "",
        "plan": "",
        "starting_tasks": [{"id": "task-1", "name": "Demo", "prompt": "Demo prompt", "created": "", "creator": "", "logo": ""}],
    }
    errors = validate_generated_team(REPO_ROOT / "data" / "agent_teams" / "demo.json", sample)
    if errors:
        print("self-test failed:", "; ".join(errors))
        return 1
    sample["agents"] = sample["agents"][:1]
    errors = validate_generated_team(REPO_ROOT / "data" / "agent_teams" / "demo.json", sample)
    if not errors:
        print("self-test failed: missing ProxyAgent was not detected")
        return 1
    print("self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Validate {SKILL_NAME} artifacts for MACE.")
    parser.add_argument("--check", action="append", choices=sorted(CHECKS), help="Run only this check; repeatable.")
    parser.add_argument("--self-test", action="store_true", help="Run validator self-test.")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    selected = args.check or list(CHECKS)
    results = [CHECKS[name]() for name in selected]
    for result in results:
        result.emit()
    failed = [result for result in results if result.failed]
    print(f"\nValidation summary for {SKILL_NAME}: {len(results) - len(failed)}/{len(results)} checks passed or skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
