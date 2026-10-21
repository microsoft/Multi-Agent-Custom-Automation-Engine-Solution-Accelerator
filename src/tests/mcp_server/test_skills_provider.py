"""
Tests for the skills directory provider registration on the MCP server.

Verifica que una skill colocada en una carpeta (SKILL.md con frontmatter) se
expone como resource `skill://<carpeta>/SKILL.md` a través del provider que la
factory registra en el servidor.
"""

from pathlib import Path

import pytest
from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider

SKILL_BODY = """---
name: demo-skill
description: A demo skill used only in tests.
---

# Demo Skill

Do the demo thing.
"""


def _write_skill(root: Path, folder: str = "demo-skill") -> Path:
    """Create <root>/<folder>/SKILL.md and return the skill folder path."""
    skill_dir = root / folder
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SKILL_BODY, encoding="utf-8")
    return skill_dir


@pytest.mark.asyncio
async def test_skill_in_temp_folder_is_listed_as_resource(tmp_path):
    """Una skill en una carpeta temporal se lista como resource del servidor."""
    _write_skill(tmp_path)

    server = FastMCP("test-skills")
    server.add_provider(SkillsDirectoryProvider(roots=tmp_path))

    resources = await server.list_resources()
    uris = {str(r.uri) for r in resources}

    # El nombre del resource es el nombre de la CARPETA, no el frontmatter.
    assert "skill://demo-skill/SKILL.md" in uris


@pytest.mark.asyncio
async def test_empty_skills_root_lists_no_skill_resources(tmp_path):
    """Un root sin skills no agrega resources skill:// (provider inerte)."""
    server = FastMCP("test-skills-empty")
    server.add_provider(SkillsDirectoryProvider(roots=tmp_path))

    resources = await server.list_resources()
    skill_uris = [str(r.uri) for r in resources if str(r.uri).startswith("skill://")]

    assert skill_uris == []


@pytest.mark.asyncio
async def test_factory_registers_skills_provider(mcp_factory):
    """La factory registra un SkillsDirectoryProvider apuntando a src/mcp_server/skills."""
    server = mcp_factory.create_mcp_server(name="factory-skills")

    # El provider resuelve la ruta junto a core/factory.py -> mcp_server/skills,
    # así que debe exponer las skills incluidas en el repo.
    resources = await server.list_resources()
    skill_resources = [r for r in resources if str(r.uri).startswith("skill://")]

    # Debe exponer al menos la skill using-the-toolbox incluida en el repo.
    uris = {str(r.uri) for r in skill_resources}
    assert "skill://using-the-toolbox/SKILL.md" in uris
