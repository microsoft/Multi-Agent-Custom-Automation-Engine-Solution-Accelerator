"""
Integration tests for FoundryAgentTemplate functionality.
Tests Bing search, RAG, MCP tools, and Code Interpreter capabilities.
"""
# pylint: disable=E0401, E0611, C0413

import sys
from pathlib import Path

import pytest

# Add the backend path to sys.path so we can import v3 modules
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Now import from the v3 package
from src.backend.v3.magentic_agents.foundry_agent import FoundryAgentTemplate
from src.backend.v3.magentic_agents.models.agent_models import (BingConfig, MCPConfig,
                                                    SearchConfig)


class TestFoundryAgentIntegration:
    """Integration tests for FoundryAgentTemplate capabilities."""

    def get_agent_configs(self):
        """Create agent configurations from environment variables."""
        # These will return None if env vars are missing, which is expected behavior
        mcp_config = MCPConfig.from_env()
        #bing_config = BingConfig.from_env()
        search_config = SearchConfig.from_env()
        
        return {
            'mcp_config': mcp_config,
            #'bing_config': bing_config,
            'search_config': search_config
        }

    # Creating agent for each test for now due to "E Failed: Bing search test failed 
    # with error: The thread could not be created due to an error response from the 
    # service" error when trying to use Pytest fixtures to share agent instance.
    async def create_foundry_agent(self):
        """Create and initialize a FoundryAgentTemplate for testing."""
        agent_configs = self.get_agent_configs()
        
        agent_name = "TestFoundryAgent"
        agent_description = "A comprehensive research assistant for integration testing"
        agent_instructions = (
            "You are an Enhanced Research Agent with multiple information sources:\n"
            "1. Bing search for current web information and recent events\n"
            "2. Azure AI Search for internal knowledge base and documents\n"
            "3. MCP tools for specialized data access\n\n"
            "Search Strategy:\n"
            "- Use Azure AI Search first for internal/proprietary information\n"
            "- Use Bing search for current events, recent news, and public information\n"
            "- Always cite your sources and specify which search method provided the information\n"
            "- Provide comprehensive answers combining multiple sources when relevant\n"
            "- Ask for clarification only if the task is genuinely ambiguous"
        )
        model_deployment_name = "gpt-4.1"

        agent = FoundryAgentTemplate(
            agent_name=agent_name,
            agent_description=agent_description,
            agent_instructions=agent_instructions,
            model_deployment_name=model_deployment_name,
            enable_code_interpreter=True,
            mcp_config=agent_configs['mcp_config'],
            #bing_config=agent_configs['bing_config'],
            search_config=agent_configs['search_config']
        )

        await agent.open()
        return agent

    async def _get_agent_response(self, agent: FoundryAgentTemplate, query: str) -> str:
        """Helper method to get complete response from agent."""
        response_parts = []
        async for message in agent.invoke(query):
            if hasattr(message, 'content'):
                # Handle different content types properly
                content = message.content
                if hasattr(content, 'text'):
                    response_parts.append(str(content.text))
                elif isinstance(content, list):
                    for item in content:
                        if hasattr(item, 'text'):
                            response_parts.append(str(item.text))
                        else:
                            response_parts.append(str(item))
                else:
                    response_parts.append(str(content))
            else:
                response_parts.append(str(message))
        return ''.join(response_parts)

    @pytest.mark.asyncio
    async def test_bing_search_functionality(self):
        """Test that Bing search is working correctly."""
        agent = await self.create_foundry_agent()
        
        try:
            if not agent.bing or not agent.bing.connection_name:
                pytest.skip("Bing configuration not available - skipping Bing search test")

            query = "Please try to get todays weather in Redmond WA using a bing search.  If this succeeds, please just respond with yes, if it does not, please respond with no "
            
            response = await self._get_agent_response(agent, query)
            
            # Check that we got a meaningful response
            assert 'yes' in response.lower(), \
                "Responsed that the agent could not perform the Bing search"
            
        except Exception as e:
            pytest.fail(f"Bing search test failed with error: {e}")
        finally:
            await agent.close()

    @pytest.mark.asyncio
    async def test_rag_search_functionality(self):
        """Test that Azure AI Search RAG is working correctly."""
        """ Note: This test may fail without clear cause. Search usage seems to be intermittent. """
        agent = await self.create_foundry_agent()
        
        try:
            if not agent.search or not agent.search.connection_name:
                pytest.skip("Azure AI Search configuration not available - skipping RAG test")

            # Starter query is necessary to increase likely hood of correct response
            starter = "Do you have access to internal documents?"

            starter_response = await self._get_agent_response(agent, starter)

            query = "Can you tell me about any incident reports that have affected the warehouses??"
            
            response = await self._get_agent_response(agent, query)
            
            # Check for the expected indicator of successful RAG retrieval
            assert any(indicator in response.lower() for indicator in [
                'heavy rain', 'Logistics', '2023-07-18'
            ]), f"Expected code execution indicators in response, got: {response}\n" \
                f"Starter response - can you see RAG?: {starter_response}"

        except Exception as e:
            pytest.fail(f"RAG search test failed with error: {e}")
        finally:
            await agent.close()

    @pytest.mark.asyncio
    async def test_mcp_functionality(self):
        """Test that MCP tools are working correctly."""
        agent = await self.create_foundry_agent()
        
        try:
            if not agent.mcp or not agent.mcp.url:
                pytest.skip("MCP configuration not available - skipping MCP test")

            query = "Please greet Tom"
            
            response = await self._get_agent_response(agent, query)
            
            # Check for the expected MCP response indicator
            assert "Hello from MACAE MCP Server, Tom" in response, \
                f"Expected 'Hello from MACAE MCP Server, Tom' in MCP response, got: {response}"
            
        except Exception as e:
            pytest.fail(f"MCP test failed with error: {e}")
        finally:
            await agent.close()

    @pytest.mark.asyncio
    async def test_code_interpreter_functionality(self):
        """Test that Code Interpreter is working correctly."""
        agent = await self.create_foundry_agent()
        
        try:
            if not agent.enable_code_interpreter:
                pytest.skip("Code Interpreter not enabled - skipping code interpreter test")

            query = "Can you write and execute Python code to calculate the factorial of 5?"
            
            response = await self._get_agent_response(agent, query)
            
            # Check for indicators that code was executed
            assert any(indicator in response.lower() for indicator in [
                'factorial', '120', 'code', 'python', 'execution', 'result'
            ]), f"Expected code execution indicators in response, got: {response}"
            
            # The factorial of 5 is 120
            assert "120" in response, \
                f"Expected factorial result '120' in response, got: {response}"
            

        except Exception as e:
            pytest.fail(f"Code Interpreter test failed with error: {e}")
        finally:
            await agent.close()

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that the agent initializes correctly with available configurations."""
        agent = await self.create_foundry_agent()
        
        try:
            assert agent.agent_name == "TestFoundryAgent"
            assert agent._agent is not None, "Agent should be initialized"
            
            # Check that tools were configured based on available configs
            if agent.mcp and agent.mcp.url:
                assert agent.mcp_plugin is not None, "MCP plugin should be available"
            
        except Exception as e:
            pytest.fail(f"Agent initialization test failed with error: {e}")
        finally:
            await agent.close()

    @pytest.mark.asyncio
    async def test_agent_handles_missing_configs_gracefully(self):
        """Test that agent handles missing configurations without crashing."""
        model_deployment_name = "gpt-4.1"

        agent = FoundryAgentTemplate(
            agent_name="TestAgent",
            agent_description="Test agent",
            agent_instructions="Test instructions",
            model_deployment_name=model_deployment_name,
            enable_code_interpreter=False,
            mcp_config=None,
            #bing_config=None,
            search_config=None
        )
        
        try:
            await agent.open()
            
            # Should still be able to handle basic queries even without tools
            response = await self._get_agent_response(agent, "Hello, how are you?")
            assert len(response) > 0, "Should get some response even without tools"
            
        except Exception as e:
            pytest.fail(f"Agent should handle missing configs gracefully, but failed with: {e}")
        finally:
            await agent.close()

    @pytest.mark.asyncio
    async def test_multiple_capabilities_together(self):
        """Test that multiple capabilities can work together in a single query."""
        agent = await self.create_foundry_agent()
        
        try:
            # Only run if we have at least some capabilities available
            available_capabilities = []
            if agent.bing and agent.bing.connection_name:
                available_capabilities.append("Bing")
            if agent.search and agent.search.connection_name:
                available_capabilities.append("RAG")
            if agent.mcp and agent.mcp.url:
                available_capabilities.append("MCP")
            
            if len(available_capabilities) < 2:
                pytest.skip("Need at least 2 capabilities for integration test")

            query = "Can you search for recent AI news and also check if you have any internal documents about AI?"
            
            response = await self._get_agent_response(agent, query)
            
            # Should get a comprehensive response that may use multiple tools
            assert len(response) > 100, "Should get comprehensive response using multiple capabilities"
            
        except Exception as e:
            pytest.fail(f"Multi-capability test failed with error: {e}")
        finally:
            await agent.close()


if __name__ == "__main__":
    """Run the tests directly for debugging."""
    pytest.main([__file__, "-v", "-s"])
