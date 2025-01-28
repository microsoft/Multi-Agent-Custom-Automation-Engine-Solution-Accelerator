import logging
from typing import Any, List, Mapping

from autogen_core.base import AgentId, MessageContext
from autogen_core.components import RoutedAgent, message_handler
from autogen_core.components.models import (
    AssistantMessage,
    AzureOpenAIChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.components.tool_agent import tool_agent_caller_loop
from autogen_core.components.tools import Tool

from context.cosmos_memory import CosmosBufferedChatCompletionContext
from models.messages import (
    ActionRequest,
    ActionResponse,
    AgentMessage,
    Step,
    StepStatus,
)
from azure.monitor.events.extension import track_event


class BaseAgent(RoutedAgent):
    def __init__(
        self,
        agent_name: str,
        model_client: AzureOpenAIChatCompletionClient,
        session_id: str,
        user_id: str,
        model_context: CosmosBufferedChatCompletionContext,
        tools: List[Tool],
        tool_agent_id: AgentId,
        system_message: str,
    ):
        super().__init__(agent_name)
        self._agent_name = agent_name
        self._model_client = model_client
        self._session_id = session_id
        self._user_id = user_id
        self._model_context = model_context
        self._tools = tools
        self._tool_schema = [tool.schema for tool in tools]
        self._tool_agent_id = tool_agent_id
        self._chat_history: List[LLMMessage] = [SystemMessage(system_message)]

    @message_handler
    async def handle_action_request(
        self, message: ActionRequest, ctx: MessageContext
    ) -> ActionResponse:
        step: Step = await self._model_context.get_step(
            message.step_id, message.session_id
        )
        # TODO: Agent verbosity
        # await self._model_context.add_item(
        #     AgentMessage(
        #         session_id=message.session_id,
        #         plan_id=message.plan_id,
        #         content=f"{self._agent_name} received action request: {message.action}",
        #         source=self._agent_name,
        #         step_id=message.step_id,
        #     )
        # )
        if not step:
            return ActionResponse(
                step_id=message.step_id,
                status=StepStatus.failed,
                message="Step not found in memory.",
            )
        # TODO - here we use the action message as the source of the action, rather than step.action, as we have added a temporary conversation history to the agent, as a mechanism to give it visibility of the replies of other agents. The logic/approach needs to be thought through further to make it more consistent.
        self._chat_history.extend(
            [
                AssistantMessage(content=message.action, source="GroupChatManager"),
                UserMessage(
                    content=f"{step.human_feedback}. Now make the function call",
                    source="HumanAgent",
                ),
            ]
        )
        try:
            messages: List[LLMMessage] = await tool_agent_caller_loop(
                caller=self,
                tool_agent_id=self._tool_agent_id,
                model_client=self._model_client,
                input_messages=self._chat_history,
                tool_schema=self._tools,
                cancellation_token=ctx.cancellation_token,
            )
            logging.info("*" * 12)
            logging.info(f"LLM call completed: {messages}")
            final_message = messages[-1]
            assert isinstance(final_message.content, str)
            result = final_message.content
            await self._model_context.add_item(
                AgentMessage(
                    session_id=message.session_id,
                    user_id=self._user_id,
                    plan_id=message.plan_id,
                    content=f"{result}",
                    source=self._agent_name,
                    step_id=message.step_id,
                )
            )

            track_event(
                "Base agent - Added into the cosmos",
                {
                    "session_id": message.session_id,
                    "user_id": self._user_id,
                    "plan_id": message.plan_id,
                    "content": f"{result}",
                    "source": self._agent_name,
                    "step_id": message.step_id,
                },
            )

        except Exception as e:
            logging.exception(f"Error during LLM call: {e}")
            track_event(
                "Base agent - Error during llm call, captured into the cosmos",
                {
                    "session_id": message.session_id,
                    "user_id": self._user_id,
                    "plan_id": message.plan_id,
                    "content": f"{e}",
                    "source": self._agent_name,
                    "step_id": message.step_id,
                },
            )

            return
        print(f"Task completed: {result}")

        step.status = StepStatus.completed
        step.agent_reply = result
        await self._model_context.update_step(step)

        track_event(
            "Base agent - Updated step and updated into the cosmos",
            {
                "status": StepStatus.completed,
                "session_id": message.session_id,
                "agent_reply": f"{result}",
                "user_id": self._user_id,
                "plan_id": message.plan_id,
                "content": f"{result}",
                "source": self._agent_name,
                "step_id": message.step_id,
            },
        )

        action_response = ActionResponse(
            step_id=step.id,
            plan_id=step.plan_id,
            session_id=message.session_id,
            result=result,
            status=StepStatus.completed,
        )

        group_chat_manager_id = AgentId("group_chat_manager", self._session_id)
        await self.publish_message(action_response, group_chat_manager_id)
        # TODO: Agent verbosity
        # await self._model_context.add_item(
        #     AgentMessage(
        #         session_id=message.session_id,
        #         plan_id=message.plan_id,
        #         content=f"{self._agent_name} sending update to GroupChatManager",
        #         source=self._agent_name,
        #         step_id=message.step_id,
        #     )
        # )
        return action_response

    def save_state(self) -> Mapping[str, Any]:
        print("Saving state:")
        return {"memory": self._model_context.save_state()}

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._model_context.load_state(state["memory"])
