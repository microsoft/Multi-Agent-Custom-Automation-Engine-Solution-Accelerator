from typing import List, Optional

from context.cosmos_memory_kernel import CosmosMemoryContext
from kernel_agents.agent_base import BaseAgent
from models.messages_kernel import MessageRole, StoredMessage
from semantic_kernel.functions import KernelFunction


class SimpleChatAgent(BaseAgent):
    """A minimal chat agent for open-ended conversation."""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        memory_store: CosmosMemoryContext,
        tools: Optional[List[KernelFunction]] = None,
        system_message: Optional[str] = None,
        agent_name: str = "SimpleChatAgent",
        client=None,
        definition=None,
    ) -> None:
        super().__init__(
            agent_name=agent_name,
            session_id=session_id,
            user_id=user_id,
            memory_store=memory_store,
            tools=tools,
            system_message=system_message,
            client=client,
            definition=definition,
        )

    @staticmethod
    def default_system_message(agent_name: str | None = None) -> str:
        """Return the default system message for open-ended chat."""
        name = agent_name or "assistant"
        return (
            f"You are {name}, a friendly AI for open-ended conversation. "
            "Engage with the user naturally and helpfully."
        )

    async def handle_user_message(self, content: str) -> str:
        """Process a user message, storing it and returning the agent's reply."""
        # Record the user message locally and persist it
        self._chat_history.append({"role": "user", "content": content})
        await self._memory_store.add_item(
            StoredMessage(
                session_id=self._session_id,
                user_id=self._user_id,
                role=MessageRole.user,
                content=content,
                source=self._agent_name,
            )
        )

        # Generate a reply from the underlying model
        async_generator = self.invoke(messages=str(self._chat_history), thread=None)
        response_content = ""
        async for chunk in async_generator:
            if chunk is not None:
                response_content += str(chunk)

        # Record the assistant's response
        self._chat_history.append({"role": "assistant", "content": response_content})
        await self._memory_store.add_item(
            StoredMessage(
                session_id=self._session_id,
                user_id=self._user_id,
                role=MessageRole.assistant,
                content=response_content,
                source=self._agent_name,
            )
        )

        return response_content

