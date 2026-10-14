"""Unit tests for backend.config.mcp_config.

Covers MCPConfig / KnowledgeBaseConfig dataclasses, their ``from_env``
factories (domain URL rewriting, missing-env validation), header
generation, and the ``mcp_url`` property. The module's only external
dependency is the module-level ``config`` object (common.config.app_config),
which is patched per-test with a simple stand-in.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

import backend.config.mcp_config as mcp_config_module
from backend.config.mcp_config import (
    DOMAIN_ALLOWED_TOOLS,
    KnowledgeBaseConfig,
    MCPConfig,
    VectorStoreConfig,
)


def _mcp_config_stub(**overrides):
    base = dict(
        MCP_SERVER_ENDPOINT="https://host/mcp",
        MCP_SERVER_NAME="MCP",
        MCP_SERVER_DESCRIPTION="desc",
        AZURE_TENANT_ID="tenant",
        AZURE_CLIENT_ID="client",
        MCP_SERVER_CONNECTION_ID="conn-1",
        AZURE_AI_SEARCH_ENDPOINT="https://search.example.net",
        AZURE_AI_SEARCH_CONNECTION_NAME="",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestMCPConfigFromEnv:
    def test_from_env_no_domain(self):
        with patch.object(mcp_config_module, "config", _mcp_config_stub()):
            cfg = MCPConfig.from_env()
        assert cfg.url == "https://host/mcp"
        assert cfg.name == "MCP"
        assert cfg.description == "desc"
        assert cfg.tenant_id == "tenant"
        assert cfg.client_id == "client"
        assert cfg.connection_id == "conn-1"
        assert cfg.allowed_tools is None

    def test_from_env_domain_rewrites_mcp_suffix(self):
        with patch.object(mcp_config_module, "config", _mcp_config_stub()):
            cfg = MCPConfig.from_env(domain="hr")
        assert cfg.url == "https://host/hr/mcp"
        assert cfg.allowed_tools == DOMAIN_ALLOWED_TOOLS["hr"]

    def test_from_env_domain_without_mcp_suffix(self):
        stub = _mcp_config_stub(MCP_SERVER_ENDPOINT="https://host/base/")
        with patch.object(mcp_config_module, "config", stub):
            cfg = MCPConfig.from_env(domain="tech_support")
        assert cfg.url == "https://host/base/tech_support"
        assert cfg.allowed_tools == DOMAIN_ALLOWED_TOOLS["tech_support"]

    def test_from_env_domain_unknown_has_no_allowed_tools(self):
        with patch.object(mcp_config_module, "config", _mcp_config_stub()):
            cfg = MCPConfig.from_env(domain="does_not_exist")
        assert cfg.url == "https://host/does_not_exist/mcp"
        assert cfg.allowed_tools is None

    def test_from_env_missing_env_raises(self):
        stub = _mcp_config_stub(MCP_SERVER_ENDPOINT="")
        with patch.object(mcp_config_module, "config", stub):
            with pytest.raises(ValueError, match="missing required environment variables"):
                MCPConfig.from_env()


class TestMCPConfigHeaders:
    def test_get_headers_with_token(self):
        cfg = MCPConfig()
        headers = cfg.get_headers("abc")
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" in headers

    def test_get_headers_without_token(self):
        cfg = MCPConfig()
        assert cfg.get_headers("") == {}


class TestVectorStoreConfig:
    def test_defaults(self):
        assert VectorStoreConfig().vector_store_name == ""


class TestKnowledgeBaseConfig:
    def test_from_env_default_connection_name(self):
        with patch.object(mcp_config_module, "config", _mcp_config_stub()):
            kb = KnowledgeBaseConfig.from_env("mykb")
        assert kb.knowledge_base_name == "mykb"
        assert kb.search_endpoint == "https://search.example.net"
        assert kb.search_connection_name == "mykb-mcp"

    def test_from_env_explicit_connection_name(self):
        stub = _mcp_config_stub(AZURE_AI_SEARCH_CONNECTION_NAME="shared-conn")
        with patch.object(mcp_config_module, "config", stub):
            kb = KnowledgeBaseConfig.from_env("mykb")
        assert kb.search_connection_name == "shared-conn"

    def test_from_env_missing_endpoint_raises(self):
        stub = _mcp_config_stub(AZURE_AI_SEARCH_ENDPOINT="")
        with patch.object(mcp_config_module, "config", stub):
            with pytest.raises(ValueError):
                KnowledgeBaseConfig.from_env("mykb")

    def test_from_env_missing_kb_name_raises(self):
        with patch.object(mcp_config_module, "config", _mcp_config_stub()):
            with pytest.raises(ValueError):
                KnowledgeBaseConfig.from_env("")

    def test_mcp_url(self):
        kb = KnowledgeBaseConfig(
            knowledge_base_name="kb1",
            search_endpoint="https://search.example.net/",
        )
        assert kb.mcp_url == (
            "https://search.example.net/knowledgebases/kb1/mcp"
            "?api-version=2025-11-01-preview"
        )


class TestDomainAllowedTools:
    def test_known_domains_present(self):
        for domain in ("hr", "tech_support", "marketing", "product", "image"):
            assert domain in DOMAIN_ALLOWED_TOOLS
            assert isinstance(DOMAIN_ALLOWED_TOOLS[domain], list)
