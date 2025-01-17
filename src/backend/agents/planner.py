# planner_agent.py
import json
import logging
import uuid
from typing import List, Optional

from autogen_core.base import MessageContext
from autogen_core.components import RoutedAgent, default_subscription, message_handler
from autogen_core.components.models import (
    AzureOpenAIChatCompletionClient,
    LLMMessage,
    UserMessage,
)
from pydantic import BaseModel

from context.cosmos_memory import CosmosBufferedChatCompletionContext
from models.messages import (
    AgentMessage,
    HumanClarification,
    BAgentType,
    InputTask,
    Plan,
    PlanStatus,
    Step,
    StepStatus,
    HumanFeedbackStatus,
)

from azure.monitor.events.extension import track_event


@default_subscription
class PlannerAgent(RoutedAgent):
    def __init__(
        self,
        model_client: AzureOpenAIChatCompletionClient,
        session_id: str,
        user_id: str,
        memory: CosmosBufferedChatCompletionContext,
        available_agents: List[BAgentType],
        agent_tools_list: List[str] = None,
    ):
        super().__init__("PlannerAgent")
        self._model_client = model_client
        self._session_id = session_id
        self._user_id = user_id
        self._memory = memory
        self._available_agents = available_agents
        self._agent_tools_list = agent_tools_list

    @message_handler
    async def handle_input_task(self, message: InputTask, ctx: MessageContext) -> Plan:
        """
        Handles the initial input task from the GroupChatManager.
        Generates a plan based on the input task.
        """
        instruction = self._generate_instruction(message.description)

        # Call structured message generation
        plan, steps = await self._create_structured_plan(
            [UserMessage(content=instruction, source="PlannerAgent")]
        )

        if steps:
            await self._memory.add_item(
                AgentMessage(
                    session_id=message.session_id,
                    user_id=self._user_id,
                    plan_id=plan.id,
                    content=f"Generated a plan with {len(steps)} steps. Click the blue check box beside each step to complete it, click the x to remove this step.",
                    source="PlannerAgent",
                    step_id="",
                )
            )
            logging.info(f"Plan generated: {plan.summary}")

            track_event(
                f"Planner - Generated a plan with {len(steps)} steps and added plan into the cosmos",
                {
                    "session_id": message.session_id,
                    "user_id": self._user_id,
                    "plan_id": plan.id,
                    "content": f"Generated a plan with {len(steps)} steps. Click the blue check box beside each step to complete it, click the x to remove this step.",
                    "source": "PlannerAgent",
                },
            )

            if plan.human_clarification_request is not None:
                # if the plan identified that user information was required, send a message asking the user for it
                await self._memory.add_item(
                    AgentMessage(
                        session_id=message.session_id,
                        user_id=self._user_id,
                        plan_id=plan.id,
                        content=f"I require additional information before we can proceed: {plan.human_clarification_request}",
                        source="PlannerAgent",
                        step_id="",
                    )
                )
                logging.info(
                    f"Additional information requested: {plan.human_clarification_request}"
                )

                track_event(
                    "Planner - Additional information requested and added into the cosmos",
                    {
                        "session_id": message.session_id,
                        "user_id": self._user_id,
                        "plan_id": plan.id,
                        "content": f"I require additional information before we can proceed: {plan.human_clarification_request}",
                        "source": "PlannerAgent",
                    },
                )

        return plan

    @message_handler
    async def handle_plan_clarification(
        self, message: HumanClarification, ctx: MessageContext
    ) -> None:
        """
        Handles the human clarification based on what was asked by the Planner.
        Updates the plan and stores the clarification in the session context.
        """
        # Retrieve the plan
        plan = await self._memory.get_plan_by_session(session_id=message.session_id)
        plan.human_clarification_response = message.human_clarification
        # update the plan in memory
        await self._memory.update_plan(plan)
        await self._memory.add_item(
            AgentMessage(
                session_id=message.session_id,
                user_id=self._user_id,
                plan_id="",
                content=f"{message.human_clarification}",
                source="HumanAgent",
                step_id="",
            )
        )

        track_event(
            "Planner - Store HumanAgent clarification and added into the cosmos",
            {
                "session_id": message.session_id,
                "user_id": self._user_id,
                "content": f"{message.human_clarification}",
                "source": "HumanAgent",
            },
        )

        await self._memory.add_item(
            AgentMessage(
                session_id=message.session_id,
                user_id=self._user_id,
                plan_id="",
                content="Thanks. The plan has been updated.",
                source="PlannerAgent",
                step_id="",
            )
        )
        logging.info("Plan updated with HumanClarification.")

        track_event(
            "Planner - Updated with HumanClarification and added into the cosmos",
            {
                "session_id": message.session_id,
                "user_id": self._user_id,
                "content": "Thanks. The plan has been updated.",
                "source": "PlannerAgent",
            },
        )

    def _generate_instruction(self, objective: str) -> str:
        # TODO FIX HARDCODED AGENT NAMES AT BOTTOM OF PROMPT
        agents = ", ".join([agent for agent in self._available_agents])

        """
        Generates the instruction string for the LLM.
        """
        instruction_template = f"""
        You are the Planner, an AI orchestrator that manages a group of AI agents to accomplish tasks.

        For the given objective, come up with a simple step-by-step plan.
        This plan should involve individual tasks that, if executed correctly, will yield the correct answer. Do not add any superfluous steps.
        The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

        These actions are passed to the specific agent. Make sure the action contains all the information required for the agent to execute the task.

        Your objective is:
        {objective}

        The agents you have access to are:
        {agents}

        These agents have access to the following functions:
        {self._agent_tools_list}


        The first step of your plan should be to ask the user for any additional information required to progress the rest of steps planned.

        Only use the functions provided as part of your plan. If the task is not possible with the agents and tools provided, create a step with the agent of type Exception and mark the overall status as completed.

        Do not add superfluous steps - only take the most direct path to the solution, with the minimum number of steps. Only do the minimum necessary to complete the goal.

        If there is a single function call that can directly solve the task, only generate a plan with a single step. For example, if someone asks to be granted access to a database, generate a plan with only one step involving the grant_database_access function, with no additional steps.

        When generating the action in the plan, frame the action as an instruction you are passing to the agent to execute. It should be a short, single sentence. Include the function to use. For example, "Set up an Office 365 Account for Jessica Smith. Function: set_up_office_365_account"

        Ensure the summary of the plan and the overall steps is less than 50 words.

        Identify any additional information that might be required to complete the task. Include this information in the plan in the human_clarification_request field of the plan. If it is not required, leave it as null. Do not include information that you are waiting for clarification on in the string of the action field, as this otherwise won't get updated.

        You must prioritise using the provided functions to accomplish each step. First evaluate each and every function the agents have access too. Only if you cannot find a function needed to complete the task, and you have reviewed each and every function, and determined why each are not suitable, there are two options you can take when generating the plan.
        First evaluate whether the step could be handled by a typical large language model, without any specialised functions. For example, tasks such as "add 32 to 54", or "convert this SQL code to a python script", or "write a 200 word story about a fictional product strategy".
        If a general Large Language Model CAN handle the step/required action, add a step to the plan with the action you believe would be needed, and add "EXCEPTION: No suitable function found. A generic LLM model is being used for this step." to the end of the action. Assign these steps to the GenericAgent. For example, if the task is to convert the following SQL into python code (SELECT * FROM employees;), and there is no function to convert SQL to python, write a step with the action "convert the following SQL into python code (SELECT * FROM employees;) EXCEPTION: No suitable function found. A generic LLM model is being used for this step." and assign it to the GenericAgent.
        Alternatively, if a general Large Language Model CAN NOT handle the step/required action, add a step to the plan with the action you believe would be needed, and add "EXCEPTION: Human support required to do this step, no suitable function found." to the end of the action. Assign these steps to the HumanAgent. For example, if the task is to find the best way to get from A to B, and there is no function to calculate the best route, write a step with the action "Calculate the best route from A to B. EXCEPTION: Human support required, no suitable function found." and assign it to the HumanAgent.


        Limit the plan to 6 steps or less.

        Choose from HumanAgent, HrAgent, MarketingAgent, ProcurementAgent, ProductAgent, TechSupportAgent, GenericAgent ONLY for planning your steps.

        """
        return instruction_template

    async def _create_structured_plan(
        self, messages: List[LLMMessage]
    ) -> tuple[Plan, list]:
        """
        Creates a structured plan from the LLM model response.
        """

        # Define the expected structure of the LLM response
        class StructuredOutputStep(BaseModel):
            action: str
            agent: BAgentType

        class StructuredOutputPlan(BaseModel):
            initial_goal: str
            steps: List[StructuredOutputStep]
            summary_plan_and_steps: str
            human_clarification_request: Optional[str] = None

        try:
            # Get the LLM response
            result = await self._model_client.create(
                messages,
                extra_create_args={"response_format": StructuredOutputPlan},
            )
            content = result.content

            # Parse the LLM response
            parsed_result = json.loads(content)
            structured_plan = StructuredOutputPlan(**parsed_result)

            if not structured_plan.steps:
                track_event(
                    "Planner agent - No steps found",
                    {
                        "session_id": self._session_id,
                        "user_id": self._user_id,
                        "initial_goal": structured_plan.initial_goal,
                        "overall_status": "No steps found",
                        "source": "PlannerAgent",
                        "summary": structured_plan.summary_plan_and_steps,
                        "human_clarification_request": structured_plan.human_clarification_request,
                    },
                )
                raise ValueError("No steps found")

            # Create the Plan instance
            plan = Plan(
                id=str(uuid.uuid4()),
                session_id=self._session_id,
                user_id=self._user_id,
                initial_goal=structured_plan.initial_goal,
                overall_status=PlanStatus.in_progress,
                source="PlannerAgent",
                summary=structured_plan.summary_plan_and_steps,
                human_clarification_request=structured_plan.human_clarification_request,
            )
            # Store the plan in memory
            await self._memory.add_plan(plan)

            track_event(
                "Planner - Initial plan and added into the cosmos",
                {
                    "session_id": self._session_id,
                    "user_id": self._user_id,
                    "initial_goal": structured_plan.initial_goal,
                    "overall_status": PlanStatus.in_progress,
                    "source": "PlannerAgent",
                    "summary": structured_plan.summary_plan_and_steps,
                    "human_clarification_request": structured_plan.human_clarification_request,
                },
            )

            # Create the Step instances and store them in memory
            steps = []
            for step_data in structured_plan.steps:
                step = Step(
                    plan_id=plan.id,
                    action=step_data.action,
                    agent=step_data.agent,
                    status=StepStatus.planned,
                    session_id=self._session_id,
                    user_id=self._user_id,
                    human_approval_status=HumanFeedbackStatus.requested,
                )
                await self._memory.add_step(step)
                track_event(
                    "Planner - Added planned individual step into the cosmos",
                    {
                        "plan_id": plan.id,
                        "action": step_data.action,
                        "agent": step_data.agent,
                        "status": StepStatus.planned,
                        "session_id": self._session_id,
                        "user_id": self._user_id,
                        "human_approval_status": HumanFeedbackStatus.requested,
                    },
                )
                steps.append(step)

            return plan, steps

        except Exception as e:
            logging.exception(f"Error in create_structured_plan: {e}")
            track_event(
                f"Planner - Error in create_structured_plan: {e} into the cosmos",
                {
                    "session_id": self._session_id,
                    "user_id": self._user_id,
                    "initial_goal": "Error generating plan",
                    "overall_status": PlanStatus.failed,
                    "source": "PlannerAgent",
                    "summary": f"Error generating plan: {e}",
                },
            )
            # Handle the error, possibly by creating a plan with an error step
            plan = Plan(
                id="",  # No need of plan id as the steps are not getting created
                session_id=self._session_id,
                user_id=self._user_id,
                initial_goal="Error generating plan",
                overall_status=PlanStatus.failed,
                source="PlannerAgent",
                summary=f"Error generating plan: {e}",
            )
            return plan, []
