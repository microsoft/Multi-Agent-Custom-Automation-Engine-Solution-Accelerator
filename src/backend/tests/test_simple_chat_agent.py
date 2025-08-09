import os
import pytest

# Set required environment variables before importing the agent
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://mock-endpoint")
os.environ.setdefault("AZURE_AI_SUBSCRIPTION_ID", "sub")
os.environ.setdefault("AZURE_AI_RESOURCE_GROUP", "rg")
os.environ.setdefault("AZURE_AI_PROJECT_NAME", "proj")
os.environ.setdefault("AZURE_AI_AGENT_ENDPOINT", "https://agent-endpoint")

from kernel_agents.simple_chat_agent import SimpleChatAgent
from models.messages_kernel import MessageRole


class DummyMemoryStore:
    def __init__(self):
        self.items = []

    async def add_item(self, item):
        self.items.append(item)


@pytest.mark.asyncio
async def test_handle_user_message_stores_and_replies():
    memory_store = DummyMemoryStore()
    agent = SimpleChatAgent(session_id="s", user_id="u", memory_store=memory_store)

    async def fake_invoke(self, messages=None, thread=None):
        yield "Hi there!"

    agent.invoke = fake_invoke.__get__(agent, SimpleChatAgent)

    response = await agent.handle_user_message("Hello")

    assert response == "Hi there!"
    assert agent._chat_history[-2:] == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    assert len(memory_store.items) == 2
    assert memory_store.items[0].content == "Hello"
    assert memory_store.items[0].role == MessageRole.user
    assert memory_store.items[1].content == "Hi there!"
    assert memory_store.items[1].role == MessageRole.assistant

