import json
from typing import Optional

import semantic_kernel as sk
from pydantic import BaseModel

from common.models.messages_kernel import Step
from common.database.database_factory import DatabaseFactory

common_agent_system_message = "If you do not have the information for the arguments of the function you need to call, do not call the function. Instead, respond back to the user requesting further information. You must not hallucinate or invent any of the information used as arguments in the function. For example, if you need to call a function that requires a delivery address, you must not generate 123 Example St. You must skip calling functions and return a clarification message along the lines of: Sorry, I'm missing some information I need to help you with that. Could you please provide the delivery address so I can do that for you?"


class FSMStateAndTransition(BaseModel):
    """Model for state and transition in a finite state machine."""

    identifiedTargetState: str
    identifiedTargetTransition: str


async def extract_and_update_transition_states(
    step: Step,
    session_id: str,
    user_id: str,
    planner_dynamic_or_workflow: str,
    kernel: sk.Kernel,
) -> Optional[Step]:
    """
    This function extracts the identified target state and transition from the LLM response and updates
    the step with the identified target state and transition. This is reliant on the agent_reply already being present.

    Args:
        step: The step to update
        session_id: The current session ID
        user_id: The user ID
        planner_dynamic_or_workflow: Type of planner
        kernel: The semantic kernel instance

    Returns:
        The updated step or None if extraction fails
    """
    planner_dynamic_or_workflow = "workflow"
    if planner_dynamic_or_workflow == "workflow":
        cosmos = await DatabaseFactory.get_database()

        # Create chat history for the semantic kernel completion
        messages = [
            {"role": "assistant", "content": step.action},
            {"role": "assistant", "content": step.agent_reply},
            {
                "role": "assistant",
                "content": "Based on the above conversation between two agents, I need you to identify the identifiedTargetState and identifiedTargetTransition values. Only return these values. Do not make any function calls. If you are unable to work out the next transition state, return ERROR.",
            },
        ]

        # Get the LLM response using semantic kernel
        completion_service = kernel.get_service("completion")

        try:
            completion_result = await completion_service.complete_chat_async(
                messages=messages,
                execution_settings={"response_format": {"type": "json_object"}},
            )

            content = completion_result

            # Parse the LLM response
            parsed_result = json.loads(content)
            structured_plan = FSMStateAndTransition(**parsed_result)

            # Update the step
            step.identified_target_state = structured_plan.identifiedTargetState
            step.identified_target_transition = (
                structured_plan.identifiedTargetTransition
            )

            await cosmos.update_step(step)
            return step

        except Exception as e:
            print(f"Error extracting transition states: {e}")
            return None


# The commented-out functions below would be implemented when needed
# async def set_next_viable_step_to_runnable(session_id):
#     pass

# async def initiate_replanning(session_id):
#     pass
