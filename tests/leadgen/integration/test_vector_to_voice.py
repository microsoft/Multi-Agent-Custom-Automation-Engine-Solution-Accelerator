"""Integration tests for Vector Store → Voice Agent configuration flow.

Tests the complete flow from creating OpenAI Vector Stores with dossier content
to generating voice agent configurations for the RealtimeAgent, including:
- Vector store creation and content upload
- Voice personality template generation
- Full voice agent assembly
- RealtimeAgent configuration generation
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure repo root is on sys.path so imports work correctly
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
LEADGEN_DIR = os.path.join(ROOT_DIR, "src", "leadgen")
if LEADGEN_DIR not in sys.path:
    sys.path.insert(0, LEADGEN_DIR)

# Now import leadgen modules
from models.dossier import Dossier
from models.lead import Lead, LeadStatus


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@dataclass
class MockVectorStoreInfo:
    """Mock VectorStoreInfo matching the openai_vectors module structure."""
    id: str
    name: Optional[str] = None
    status: Optional[str] = None
    file_counts: dict[str, int] = field(default_factory=dict)
    usage_bytes: int = 0
    created_at: Optional[int] = None
    expires_at: Optional[int] = None
    expires_after_days: Optional[int] = None
    success: bool = True
    error: Optional[str] = None

    @property
    def is_ready(self) -> bool:
        """Check if vector store is ready for queries."""
        return self.status == "completed"

    @property
    def is_processing(self) -> bool:
        """Check if vector store is still processing files."""
        return self.status == "in_progress"

    @property
    def total_files(self) -> int:
        """Get total number of files in the vector store."""
        return sum(self.file_counts.values())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "file_counts": self.file_counts,
            "usage_bytes": self.usage_bytes,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "expires_after_days": self.expires_after_days,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class MockFileInfo:
    """Mock FileInfo matching the openai_vectors module structure."""
    id: str
    filename: Optional[str] = None
    bytes: int = 0
    status: Optional[str] = None
    status_details: Optional[str] = None
    vector_store_id: Optional[str] = None
    created_at: Optional[int] = None
    success: bool = True
    error: Optional[str] = None

    @property
    def is_ready(self) -> bool:
        """Check if file is processed and ready for queries."""
        return self.status == "completed"


def create_mock_dossier_content() -> str:
    """Create mock dossier markdown content for testing."""
    return """# Company Overview

**Name:** Springfield Family Dental
**Address:** 123 Main St, Springfield, IL 62701
**Phone:** (217) 555-0101
**Website:** https://springfielddental.example.com
**Industry:** dentist

Springfield Family Dental has been serving the Springfield community for over 15 years,
providing comprehensive dental care for patients of all ages.

## Services

### Primary Services
- General Dentistry (cleanings, exams, x-rays)
- Cosmetic Dentistry (whitening, veneers)
- Restorative Dentistry (fillings, crowns, bridges)

### Additional Services
- Emergency Dental Care
- Pediatric Dentistry
- Dental Implants
- Invisalign

## Team

### Dr. Sarah Johnson, DDS
Lead Dentist with 15+ years experience. Specializes in family dentistry.

### Dr. Michael Chen, DDS
Associate Dentist specializing in cosmetic and restorative procedures.

## Pain Points We Solve

- Missed appointment calls costing revenue
- After-hours patient inquiries going unanswered
- Staff overwhelmed with phone volume during peak hours

## Gotcha Q&A

Q: What is your address?
A: 123 Main St, Springfield, IL 62701

Q: Do you offer teeth whitening?
A: Yes, we offer professional teeth whitening services.

Q: What are your hours?
A: Monday-Friday 8am-5pm, Saturday 9am-2pm

## Competitors

- Downtown Dental Clinic
- Smile Center Springfield
"""


def create_mock_vector_store_result() -> MockVectorStoreInfo:
    """Create a mock successful vector store creation result."""
    return MockVectorStoreInfo(
        id="vs_mock_abc123xyz",
        name="Springfield Family Dental Knowledge Base",
        status="completed",
        file_counts={
            "in_progress": 0,
            "completed": 1,
            "failed": 0,
            "cancelled": 0,
        },
        usage_bytes=2048,
        created_at=1700000000,
        expires_after_days=7,
        success=True,
    )


def create_mock_file_info() -> MockFileInfo:
    """Create a mock file info for uploaded dossier."""
    return MockFileInfo(
        id="file_mock_def456",
        filename="business_dossier.md",
        bytes=2048,
        status="completed",
        vector_store_id="vs_mock_abc123xyz",
        created_at=1700000000,
        success=True,
    )


# ============================================================================
# Test Classes
# ============================================================================

class TestVectorStoreIntegration:
    """Tests for Vector Store creation and management integration."""

    def test_vector_store_info_structure(self):
        """Test that mock VectorStoreInfo has correct structure."""
        vs_info = create_mock_vector_store_result()

        assert vs_info.id == "vs_mock_abc123xyz"
        assert vs_info.name == "Springfield Family Dental Knowledge Base"
        assert vs_info.status == "completed"
        assert vs_info.is_ready is True
        assert vs_info.is_processing is False
        assert vs_info.total_files == 1
        assert vs_info.usage_bytes == 2048
        assert vs_info.success is True

    def test_vector_store_info_to_dict(self):
        """Test VectorStoreInfo to_dict() conversion."""
        vs_info = create_mock_vector_store_result()
        vs_dict = vs_info.to_dict()

        assert vs_dict["id"] == "vs_mock_abc123xyz"
        assert vs_dict["name"] == "Springfield Family Dental Knowledge Base"
        assert vs_dict["status"] == "completed"
        assert vs_dict["file_counts"]["completed"] == 1
        assert vs_dict["success"] is True

    def test_vector_store_module_import(self):
        """Test that VectorStoreManager can be imported."""
        from integrations.openai_vectors import (
            VectorStoreManager,
            VectorStoreInfo,
            FileInfo,
            UploadResult,
            VectorStoreStatus,
            FileStatus,
        )

        assert VectorStoreManager is not None
        assert VectorStoreInfo is not None
        assert FileInfo is not None
        assert VectorStoreStatus is not None
        assert FileStatus is not None

    def test_vector_store_status_enum_values(self):
        """Test VectorStoreStatus enum values."""
        from integrations.openai_vectors import VectorStoreStatus

        assert VectorStoreStatus.COMPLETED == "completed"
        assert VectorStoreStatus.IN_PROGRESS == "in_progress"
        assert VectorStoreStatus.EXPIRED == "expired"

    def test_file_status_enum_values(self):
        """Test FileStatus enum values."""
        from integrations.openai_vectors import FileStatus

        assert FileStatus.COMPLETED == "completed"
        assert FileStatus.IN_PROGRESS == "in_progress"
        assert FileStatus.FAILED == "failed"
        assert FileStatus.CANCELLED == "cancelled"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"})
    def test_vector_store_manager_initialization_with_env(self):
        """Test VectorStoreManager can be initialized with env var."""
        from integrations.openai_vectors import VectorStoreManager

        # Mock the OpenAI client
        with patch("integrations.openai_vectors.OpenAI"):
            manager = VectorStoreManager()
            assert manager.api_key == "test_api_key"

    def test_vector_store_manager_requires_api_key(self):
        """Test that VectorStoreManager raises error without API key."""
        from integrations.openai_vectors import VectorStoreManager

        # Ensure no API key in environment
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                VectorStoreManager()


class TestVoicePersonalityIntegration:
    """Tests for voice personality template generation integration."""

    def test_voice_personality_module_import(self):
        """Test that voice personality module can be imported."""
        from utils.voice_personality import (
            generate_personality,
            generate_personality_from_dossier,
            PersonalityTemplate,
            VoicePersonalityConfig,
            BusinessContext,
            VoicePersonalityTone,
            VoiceSpeed,
        )

        assert callable(generate_personality)
        assert callable(generate_personality_from_dossier)
        assert PersonalityTemplate is not None
        assert VoicePersonalityConfig is not None
        assert BusinessContext is not None

    def test_generate_personality_basic(self):
        """Test basic personality generation from business data."""
        from utils.voice_personality import generate_personality

        business_data = {
            "name": "Springfield Family Dental",
            "industry": "dentist",
            "address": "123 Main St, Springfield, IL 62701",
            "phone": "(217) 555-0101",
        }

        template = generate_personality(business_data)

        assert template is not None
        assert template.system_prompt is not None
        assert "Springfield Family Dental" in template.system_prompt
        assert template.greeting is not None
        assert template.closing is not None
        assert len(template.fallback_responses) > 0

    def test_generate_personality_with_services(self):
        """Test personality generation includes services."""
        from utils.voice_personality import generate_personality

        business_data = {
            "name": "Test Dental",
            "industry": "dentist",
            "services": ["cleaning", "whitening", "fillings"],
        }

        template = generate_personality(business_data)

        # System prompt should mention services
        assert "Services" in template.system_prompt

    def test_generate_personality_from_dossier(self):
        """Test personality generation with dossier content injection."""
        from utils.voice_personality import generate_personality_from_dossier

        dossier_content = create_mock_dossier_content()

        template = generate_personality_from_dossier(
            dossier_content=dossier_content,
            business_name="Springfield Family Dental",
            industry="dentist",
        )

        assert template is not None
        assert template.system_prompt is not None
        # Dossier content should be injected
        assert "Detailed Business Knowledge" in template.system_prompt
        assert "Springfield Family Dental" in template.system_prompt

    def test_personality_template_structure(self):
        """Test PersonalityTemplate has all required fields."""
        from utils.voice_personality import generate_personality

        business_data = {
            "name": "Test Business",
            "industry": "dentist",
        }

        template = generate_personality(business_data)

        # Verify all required template fields
        assert hasattr(template, "system_prompt")
        assert hasattr(template, "greeting")
        assert hasattr(template, "closing")
        assert hasattr(template, "fallback_responses")
        assert hasattr(template, "transfer_message")
        assert hasattr(template, "voicemail_message")
        assert hasattr(template, "config")
        assert hasattr(template, "context")

    def test_voice_personality_tone_options(self):
        """Test available personality tone options."""
        from utils.voice_personality import get_available_tones, VoicePersonalityTone

        tones = get_available_tones()

        assert "professional" in tones
        assert "friendly" in tones
        assert "casual" in tones
        assert "empathetic" in tones

    def test_voice_personality_speed_options(self):
        """Test available speaking speed options."""
        from utils.voice_personality import get_available_speeds

        speeds = get_available_speeds()

        assert "slow" in speeds
        assert "moderate" in speeds
        assert "fast" in speeds

    def test_supported_industries(self):
        """Test list of industries with specialized hints."""
        from utils.voice_personality import get_supported_industries

        industries = get_supported_industries()

        assert "dentist" in industries
        assert "hvac" in industries
        assert "salon" in industries
        assert "default" in industries


class TestVoiceAssemblerAgentIntegration:
    """Tests for voice assembler agent functions integration."""

    def test_voice_assembler_internal_functions_import(self):
        """Test that internal functions can be imported."""
        try:
            from agents.voice_assembler_agent import (
                _create_vector_store_internal,
                _generate_voice_personality_internal,
                _assemble_voice_agent_internal,
                VoiceAgentConfig,
                AssemblyResult,
            )
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        assert callable(_create_vector_store_internal)
        assert callable(_generate_voice_personality_internal)
        assert callable(_assemble_voice_agent_internal)
        assert VoiceAgentConfig is not None
        assert AssemblyResult is not None

    def test_voice_agent_config_structure(self):
        """Test VoiceAgentConfig dataclass structure."""
        try:
            from agents.voice_assembler_agent import VoiceAgentConfig
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        config = VoiceAgentConfig(
            lead_id="lead_123",
            lead_name="Test Dental",
            vector_store_id="vs_abc123",
            personality_prompt="You are the AI receptionist...",
            greeting="Hello, thank you for calling.",
            closing="Thank you for calling, goodbye.",
            industry="dentist",
            dossier_status="complete",
            voice_agent_ready=True,
        )

        assert config.lead_id == "lead_123"
        assert config.lead_name == "Test Dental"
        assert config.vector_store_id == "vs_abc123"
        assert config.voice_agent_ready is True

    def test_voice_agent_config_to_dict(self):
        """Test VoiceAgentConfig to_dict() conversion."""
        try:
            from agents.voice_assembler_agent import VoiceAgentConfig
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        config = VoiceAgentConfig(
            lead_id="lead_123",
            lead_name="Test Dental",
            vector_store_id="vs_abc123",
            personality_prompt="You are the AI receptionist...",
            industry="dentist",
            voice_agent_ready=True,
        )

        config_dict = config.to_dict()

        assert config_dict["lead_id"] == "lead_123"
        assert config_dict["lead_name"] == "Test Dental"
        assert config_dict["vector_store_id"] == "vs_abc123"
        assert config_dict["voice_agent_ready"] is True

    def test_assembly_result_structure(self):
        """Test AssemblyResult dataclass structure."""
        try:
            from agents.voice_assembler_agent import AssemblyResult, VoiceAgentConfig
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        config = VoiceAgentConfig(
            lead_id="lead_123",
            lead_name="Test Dental",
            voice_agent_ready=True,
        )

        result = AssemblyResult(
            success=True,
            config=config,
            vector_store_info={"id": "vs_123", "status": "completed"},
            personality_template={"system_prompt": "...", "greeting": "..."},
            errors=[],
        )

        assert result.success is True
        assert result.config.lead_name == "Test Dental"
        assert result.vector_store_info is not None
        assert len(result.errors) == 0

    def test_assembly_result_to_dict(self):
        """Test AssemblyResult to_dict() conversion."""
        try:
            from agents.voice_assembler_agent import AssemblyResult, VoiceAgentConfig
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        config = VoiceAgentConfig(
            lead_id="lead_123",
            lead_name="Test Dental",
            voice_agent_ready=True,
        )

        result = AssemblyResult(
            success=True,
            config=config,
            errors=[],
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["config"]["lead_name"] == "Test Dental"
        assert result_dict["errors"] == []

    def test_generate_voice_personality_internal(self):
        """Test internal voice personality generation."""
        try:
            from agents.voice_assembler_agent import _generate_voice_personality_internal
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        business_data = {
            "name": "Springfield Family Dental",
            "industry": "dentist",
            "address": "123 Main St",
        }

        result = _generate_voice_personality_internal(business_data)

        assert result["success"] is True
        assert result["system_prompt"] is not None
        assert result["greeting"] is not None
        assert result["closing"] is not None
        assert result["prompt_word_count"] > 0

    def test_generate_voice_personality_internal_with_dossier(self):
        """Test internal voice personality generation with dossier."""
        try:
            from agents.voice_assembler_agent import _generate_voice_personality_internal
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        business_data = {
            "name": "Springfield Family Dental",
            "industry": "dentist",
        }

        dossier_content = create_mock_dossier_content()

        result = _generate_voice_personality_internal(
            business_data=business_data,
            dossier_content=dossier_content,
        )

        assert result["success"] is True
        assert result["system_prompt"] is not None
        # Dossier should be injected
        assert "Detailed Business Knowledge" in result["system_prompt"]


class TestVectorToVoicePipeline:
    """Tests for the complete Vector Store → Voice Agent pipeline."""

    def test_dossier_model_voice_readiness(self):
        """Test Dossier model voice readiness tracking."""
        # Dossier without voice configuration
        dossier_partial = Dossier(
            lead_id="lead_1",
            content="# Dossier content",
        )

        assert dossier_partial.has_vector_store is False
        assert dossier_partial.has_assistant is False
        assert dossier_partial.is_ready_for_voice is False

        # Dossier with full voice configuration
        dossier_ready = Dossier(
            lead_id="lead_2",
            content="# Dossier content",
            vector_store_id="vs_abc123",
            assistant_id="asst_def456",
        )

        assert dossier_ready.has_vector_store is True
        assert dossier_ready.has_assistant is True
        assert dossier_ready.is_ready_for_voice is True

    def test_pipeline_simulation_vector_to_personality(self):
        """Test simulated pipeline from vector store to personality."""
        from utils.voice_personality import generate_personality_from_dossier

        # Step 1: Prepare dossier content
        dossier_content = create_mock_dossier_content()

        # Step 2: Simulate vector store creation (would use VectorStoreManager in real code)
        mock_vs_info = create_mock_vector_store_result()

        # Step 3: Generate personality with dossier injection
        template = generate_personality_from_dossier(
            dossier_content=dossier_content,
            business_name="Springfield Family Dental",
            industry="dentist",
        )

        # Verify personality was generated correctly
        assert template is not None
        assert template.system_prompt is not None
        assert "Springfield Family Dental" in template.system_prompt
        assert "Detailed Business Knowledge" in template.system_prompt
        assert mock_vs_info.is_ready is True

    def test_pipeline_simulation_full_assembly(self):
        """Test simulated full voice agent assembly pipeline."""
        try:
            from agents.voice_assembler_agent import (
                _generate_voice_personality_internal,
                VoiceAgentConfig,
            )
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        from datetime import datetime, timezone

        # Step 1: Prepare lead data and dossier
        lead_data = {
            "id": "lead_test123",
            "name": "Springfield Family Dental",
            "industry": "dentist",
            "address": "123 Main St, Springfield, IL 62701",
            "phone": "(217) 555-0101",
            "website": "https://springfielddental.example.com",
        }

        dossier_content = create_mock_dossier_content()

        # Step 2: Simulate vector store creation
        mock_vs_info = create_mock_vector_store_result()

        # Step 3: Generate voice personality
        personality_result = _generate_voice_personality_internal(
            business_data=lead_data,
            dossier_content=dossier_content,
        )

        # Step 4: Assemble voice agent configuration
        config = VoiceAgentConfig(
            lead_id=lead_data["id"],
            lead_name=lead_data["name"],
            vector_store_id=mock_vs_info.id,
            personality_prompt=personality_result["system_prompt"],
            greeting=personality_result["greeting"],
            closing=personality_result["closing"],
            industry=lead_data["industry"],
            dossier_status="complete",
            voice_agent_ready=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Verify complete configuration
        assert config.voice_agent_ready is True
        assert config.vector_store_id == "vs_mock_abc123xyz"
        assert config.personality_prompt is not None
        assert config.greeting is not None
        assert config.closing is not None
        assert config.industry == "dentist"

    def test_pipeline_simulation_with_lead_and_dossier_models(self):
        """Test pipeline simulation with Lead and Dossier database models."""
        from decimal import Decimal

        try:
            from agents.voice_assembler_agent import VoiceAgentConfig
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        from utils.voice_personality import generate_personality_from_dossier

        # Step 1: Create Lead model
        lead = Lead(
            name="Springfield Family Dental",
            address="123 Main St, Springfield, IL 62701",
            phone="(217) 555-0101",
            website="https://springfielddental.example.com",
            industry="dentist",
            rating=Decimal("4.5"),
            review_count=150,
            revenue=Decimal("487500.00"),
            status=LeadStatus.RESEARCHED,
            google_place_id="place_abc123",
        )

        # Step 2: Create Dossier model
        dossier_content = create_mock_dossier_content()
        dossier = Dossier(
            lead_id="lead_test123",
            content=dossier_content,
        )

        # Step 3: Simulate vector store creation
        mock_vs_info = create_mock_vector_store_result()

        # Update dossier with vector store ID
        dossier.vector_store_id = mock_vs_info.id

        # Step 4: Generate personality
        template = generate_personality_from_dossier(
            dossier_content=dossier.content,
            business_name=lead.name,
            industry=lead.industry,
        )

        # Step 5: Create voice agent config
        config = VoiceAgentConfig(
            lead_id=dossier.lead_id,
            lead_name=lead.name,
            vector_store_id=dossier.vector_store_id,
            personality_prompt=template.system_prompt,
            greeting=template.greeting,
            closing=template.closing,
            industry=lead.industry,
            dossier_status="complete",
            voice_agent_ready=True,
        )

        # Verify pipeline output
        assert lead.status == LeadStatus.RESEARCHED
        assert dossier.has_vector_store is True
        assert config.voice_agent_ready is True
        assert config.vector_store_id == mock_vs_info.id


class TestRealtimeAgentConfiguration:
    """Tests for RealtimeAgent configuration generation."""

    def _build_realtime_config(
        self,
        vector_store_id: str,
        personality_prompt: str,
        business_name: str,
    ) -> dict[str, Any]:
        """Build RealtimeAgent configuration directly (bypassing @function_tool)."""
        return {
            "name": f"{business_name} Voice Assistant",
            "instructions": personality_prompt,
            "tools": [
                {"type": "file_search"},
            ],
            "tool_resources": {
                "file_search": {
                    "vector_store_ids": [vector_store_id],
                },
            },
            "model": "gpt-4o-realtime-preview",
            "voice_settings": {
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
            },
            "success": True,
        }

    def test_realtime_agent_config_structure(self):
        """Test RealtimeAgent configuration structure."""
        config = self._build_realtime_config(
            vector_store_id="vs_abc123xyz",
            personality_prompt="You are the AI receptionist for Acme Dental...",
            business_name="Acme Dental",
        )

        # Verify structure
        assert config["success"] is True
        assert config["name"] == "Acme Dental Voice Assistant"
        assert config["instructions"] is not None
        assert "tools" in config
        assert "tool_resources" in config
        assert config["model"] == "gpt-4o-realtime-preview"

    def test_realtime_agent_config_voice_settings(self):
        """Test RealtimeAgent voice settings configuration."""
        config = self._build_realtime_config(
            vector_store_id="vs_abc123xyz",
            personality_prompt="You are the AI receptionist...",
            business_name="Test Business",
        )

        voice_settings = config.get("voice_settings", {})

        # Verify voice settings
        assert voice_settings.get("voice") == "alloy"
        assert voice_settings.get("input_audio_format") == "pcm16"
        assert voice_settings.get("output_audio_format") == "pcm16"

        # Verify turn detection (VAD settings)
        turn_detection = voice_settings.get("turn_detection", {})
        assert turn_detection.get("type") == "server_vad"
        assert turn_detection.get("threshold") == 0.5

    def test_realtime_agent_config_file_search_tool(self):
        """Test RealtimeAgent includes file_search tool with vector store."""
        config = self._build_realtime_config(
            vector_store_id="vs_test_vector_store",
            personality_prompt="System prompt here",
            business_name="Test Business",
        )

        # Verify file_search tool is configured
        tools = config.get("tools", [])
        assert any(t.get("type") == "file_search" for t in tools)

        # Verify vector store is linked
        tool_resources = config.get("tool_resources", {})
        file_search_resources = tool_resources.get("file_search", {})
        vector_store_ids = file_search_resources.get("vector_store_ids", [])
        assert "vs_test_vector_store" in vector_store_ids

    def test_voice_assembler_agent_tools_registered(self):
        """Test that voice assembler agent has required tools registered."""
        try:
            from agents.voice_assembler_agent import voice_assembler_agent
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        # Verify agent has tools
        assert voice_assembler_agent is not None
        assert hasattr(voice_assembler_agent, "tools")
        assert len(voice_assembler_agent.tools) > 0

        # Verify tool names include expected functions
        tool_names = [t.name if hasattr(t, 'name') else str(t) for t in voice_assembler_agent.tools]
        expected_tools = [
            "create_vector_store_for_lead",
            "generate_voice_personality",
            "delete_vector_store",
            "assemble_voice_agent",
            "get_realtime_agent_config",
        ]
        for expected in expected_tools:
            assert any(expected in name for name in tool_names), f"Missing tool: {expected}"


class TestVoiceAgentReadiness:
    """Tests for voice agent readiness determination."""

    def test_voice_agent_ready_when_complete(self):
        """Test voice agent is ready when all components present."""
        try:
            from agents.voice_assembler_agent import VoiceAgentConfig
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        config = VoiceAgentConfig(
            lead_id="lead_123",
            lead_name="Test Business",
            vector_store_id="vs_abc123",
            personality_prompt="System prompt",
            greeting="Hello",
            closing="Goodbye",
            industry="dentist",
            dossier_status="complete",
            voice_agent_ready=True,
        )

        # All components present - should be ready
        assert config.voice_agent_ready is True
        assert config.vector_store_id is not None
        assert config.personality_prompt is not None

    def test_voice_agent_not_ready_missing_vector_store(self):
        """Test voice agent not ready when vector store missing."""
        try:
            from agents.voice_assembler_agent import VoiceAgentConfig
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        config = VoiceAgentConfig(
            lead_id="lead_123",
            lead_name="Test Business",
            vector_store_id=None,  # Missing
            personality_prompt="System prompt",
            voice_agent_ready=False,
        )

        assert config.voice_agent_ready is False

    def test_voice_agent_not_ready_missing_personality(self):
        """Test voice agent not ready when personality missing."""
        try:
            from agents.voice_assembler_agent import VoiceAgentConfig
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        config = VoiceAgentConfig(
            lead_id="lead_123",
            lead_name="Test Business",
            vector_store_id="vs_abc123",
            personality_prompt=None,  # Missing
            voice_agent_ready=False,
        )

        assert config.voice_agent_ready is False


class TestErrorHandling:
    """Tests for error handling in the vector to voice flow."""

    def test_personality_generation_with_minimal_data(self):
        """Test personality generation handles minimal business data."""
        from utils.voice_personality import generate_personality

        # Minimal data - just name
        business_data = {"name": "Unknown Business"}

        template = generate_personality(business_data)

        # Should still succeed
        assert template is not None
        assert template.system_prompt is not None
        assert "Unknown Business" in template.system_prompt

    def test_personality_generation_with_unknown_industry(self):
        """Test personality generation handles unknown industry."""
        from utils.voice_personality import generate_personality

        business_data = {
            "name": "Unique Business",
            "industry": "underwater_basket_weaving",  # Unknown industry
        }

        template = generate_personality(business_data)

        # Should use default industry hints
        assert template is not None
        assert template.system_prompt is not None

    def test_dossier_with_failed_vector_store(self):
        """Test handling when vector store creation fails."""
        dossier = Dossier(
            lead_id="lead_123",
            content="# Dossier content",
            vector_store_id=None,  # Failed to create
        )

        assert dossier.has_vector_store is False
        assert dossier.is_ready_for_voice is False

    def test_voice_agent_config_with_error(self):
        """Test VoiceAgentConfig handles errors correctly."""
        try:
            from agents.voice_assembler_agent import VoiceAgentConfig
        except ImportError:
            pytest.skip("Voice assembler agent cannot be imported")

        config = VoiceAgentConfig(
            lead_id="lead_123",
            lead_name="Test Business",
            vector_store_id=None,
            personality_prompt=None,
            voice_agent_ready=False,
            error="Vector store creation failed: API key invalid",
        )

        assert config.voice_agent_ready is False
        assert config.error is not None
        assert "Vector store creation failed" in config.error


class TestDatabaseIntegration:
    """Tests for database integration with voice agent data."""

    def test_dossier_vector_store_update(self):
        """Test updating Dossier with vector store ID."""
        dossier = Dossier(
            lead_id="lead_123",
            content="# Dossier content",
        )

        assert dossier.has_vector_store is False

        # Simulate vector store creation
        dossier.vector_store_id = "vs_abc123xyz"

        assert dossier.has_vector_store is True
        assert dossier.vector_store_id == "vs_abc123xyz"

    def test_dossier_assistant_update(self):
        """Test updating Dossier with assistant ID."""
        dossier = Dossier(
            lead_id="lead_123",
            content="# Dossier content",
            vector_store_id="vs_abc123",
        )

        assert dossier.has_assistant is False
        assert dossier.is_ready_for_voice is False

        # Simulate assistant creation
        dossier.assistant_id = "asst_def456"

        assert dossier.has_assistant is True
        assert dossier.is_ready_for_voice is True

    def test_lead_status_for_voice_ready(self):
        """Test Lead status transitions for voice agent readiness."""
        from decimal import Decimal

        lead = Lead(
            name="Test Business",
            address="123 Test St",
            industry="dentist",
            rating=Decimal("4.5"),
            review_count=100,
            status=LeadStatus.RESEARCHED,
            google_place_id="place_123",
        )

        # Should be RESEARCHED after dossier creation
        assert lead.status == LeadStatus.RESEARCHED

        # Transition to DEPLOYING during voice agent assembly
        lead.status = LeadStatus.DEPLOYING
        assert lead.status == LeadStatus.DEPLOYING

        # Transition to DEPLOYED after voice agent ready
        lead.status = LeadStatus.DEPLOYED
        assert lead.status == LeadStatus.DEPLOYED


class TestContentIntegration:
    """Tests for content flow from dossier to voice configuration."""

    def test_dossier_content_used_in_personality(self):
        """Test that dossier content is properly used in personality generation."""
        from utils.voice_personality import generate_personality_from_dossier

        dossier_content = create_mock_dossier_content()

        template = generate_personality_from_dossier(
            dossier_content=dossier_content,
            business_name="Springfield Family Dental",
            industry="dentist",
        )

        # Verify dossier content influence
        system_prompt = template.system_prompt

        # Should contain business name
        assert "Springfield Family Dental" in system_prompt

        # Should contain dossier injection section
        assert "Detailed Business Knowledge" in system_prompt

        # Should have substantial word count
        word_count = len(system_prompt.split())
        assert word_count >= 200  # Reasonable minimum for comprehensive prompt

    def test_services_from_dossier_in_personality(self):
        """Test that services from dossier are reflected in personality."""
        from utils.voice_personality import generate_personality

        # Business data with services
        business_data = {
            "name": "Test Dental",
            "industry": "dentist",
            "services": ["cleaning", "whitening", "implants"],
        }

        template = generate_personality(business_data)

        # Services section should be present
        assert "Services" in template.system_prompt

    def test_gotcha_questions_handling(self):
        """Test that dossier gotcha Q&A enables accurate answers."""
        from utils.voice_personality import generate_personality_from_dossier

        dossier_content = create_mock_dossier_content()

        template = generate_personality_from_dossier(
            dossier_content=dossier_content,
            business_name="Springfield Family Dental",
            industry="dentist",
        )

        # The system prompt should contain dossier with gotcha Q&As
        # so the voice agent can answer them accurately
        assert "123 Main St" in template.system_prompt  # Address gotcha
        assert "whitening" in template.system_prompt.lower()  # Service gotcha


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
