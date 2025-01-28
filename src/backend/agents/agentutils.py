import json

from autogen_core.components.models import (
    AssistantMessage,
    AzureOpenAIChatCompletionClient,
)
from pydantic import BaseModel

from context.cosmos_memory import CosmosBufferedChatCompletionContext
from models.messages import Step

common_agent_system_message = "If you do not have the information for the arguments of the function you need to call, do not call the function. Instead, respond back to the user requesting further information. You must not hallucinate or invent any of the information used as arguments in the function. For example, if you need to call a function that requires a delivery address, you must not generate 123 Example St. You must skip calling functions and return a clarification message along the lines of: Sorry, I'm missing some information I need to help you with that. Could you please provide the delivery address so I can do that for you?"


async def extract_and_update_transition_states(
    step: Step,
    session_id: str,
    user_id: str,
    planner_dynamic_or_workflow: str,
    model_client: AzureOpenAIChatCompletionClient,
):
    """
    This function extracts the identified target state and transition from the LLM response and updates the step with the identified target state and transition. This is reliant on the agent_reply already being present.
    """
    planner_dynamic_or_workflow = "workflow"
    if planner_dynamic_or_workflow == "workflow":

        class FSMStateAndTransition(BaseModel):
            identifiedTargetState: str
            identifiedTargetTransition: str

        cosmos = CosmosBufferedChatCompletionContext(session_id or "", user_id)
        combined_LLM_messages = [
            AssistantMessage(content=step.action, source="GroupChatManager")
        ]
        combined_LLM_messages.extend(
            [AssistantMessage(content=step.agent_reply, source="AgentResponse")]
        )
        combined_LLM_messages.extend(
            [
                AssistantMessage(
                    content="Based on the above conversation between two agents, I need you to identify the identifiedTargetState and identifiedTargetTransition values. Only return these values. Do not make any function calls. If you are unable to work out the next transition state, return ERROR.",
                    source="GroupChatManager",
                )
            ]
        )

        # TODO - from local testing, this step is often causing the app to hang. It's unclear why- often the first time it fails when running a workflow that requires human input. If the app is manually restarted, it works the second time. However this is not consistent- sometimes it will work fine the first time. It may be the LLM generating some invalid characters which is causing errors on the JSON formatting. However, even when attempting a timeout and retry, the timeout with asnycio would never trigger. It's unclear what the issue is here.
        # Get the LLM response
        llm_temp_result = await model_client.create(
            combined_LLM_messages,
            extra_create_args={"response_format": FSMStateAndTransition},
        )
        content = llm_temp_result.content

        # Parse the LLM response
        parsed_result = json.loads(content)
        structured_plan = FSMStateAndTransition(**parsed_result)

        # update the steps
        step.identified_target_state = structured_plan.identifiedTargetState
        step.identified_target_transition = structured_plan.identifiedTargetTransition

        await cosmos.update_step(step)
        return step


# async def set_next_viable_step_to_runnable(session_id):
#     cosmos = CosmosBufferedChatCompletionContext(session_id)
#     plan_with_steps = await cosmos.get_plan_with_steps(session_id)
#     if plan_with_steps.overall_status != PlanStatus.completed:
#         for step_object in plan_with_steps.steps:
#             if step_object.status not in [StepStatus.rejected, StepStatus.completed]:
#                 step_object.runnable = True
#                 await cosmos.update_step(step_object)
#                 break


# async def initiate_replanning(session_id):
#     from utils import handle_input_task_wrapper

#     cosmos = CosmosBufferedChatCompletionContext(session_id)
#     plan_with_steps = await cosmos.get_plan_with_steps(session_id)
#     input_task = InputTask(
#         session_id=plan_with_steps.session_id,
#         description=plan_with_steps.initial_goal,
#         planner_type=plan_with_steps.planner_type,
#         new_plan_or_replanning="replanning",
#         human_comments_on_overall_plan=plan_with_steps.human_comments_on_overall_plan,
#         planner_dynamic_or_workflow=plan_with_steps.planner_dynamic_or_workflow,
#         workflowName=plan_with_steps.workflowName,
#     )
#     await handle_input_task_wrapper(input_task)
