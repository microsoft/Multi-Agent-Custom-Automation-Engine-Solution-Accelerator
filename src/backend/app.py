# app.py
import asyncio
import logging
import os
import uuid
from typing import List, Optional
from middleware.health_check import HealthCheckMiddleware
from autogen_core.base import AgentId
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from auth.auth_utils import get_authenticated_user_details
from config import Config
from context.cosmos_memory import CosmosBufferedChatCompletionContext
from models.messages import (
    BaseDataModel,
    HumanFeedback,
    HumanClarification,
    InputTask,
    Plan,
    Session,
    Step,
    AgentMessage,
    PlanWithSteps,
)
from utils import initialize_runtime_and_context, retrieve_all_agent_tools, rai_success
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from azure.monitor.opentelemetry import configure_azure_monitor
from logging import getLogger, INFO
from azure.monitor.events.extension import track_event

configure_azure_monitor(
    connection_string=os.getenv("APPLICATIONINSIGHTS_INSTRUMENTATION_KEY")
)


logger = getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Suppress INFO logs from 'azure.core.pipeline.policies.http_logging_policy'
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)
logging.getLogger("azure.identity.aio._internal").setLevel(logging.WARNING)

# Suppress info logs from OpenTelemetry exporter
logging.getLogger("azure.monitor.opentelemetry.exporter.export._base").setLevel(logging.WARNING)

# Initialize the FastAPI app
app = FastAPI()

frontend_url = Config.FRONTEND_SITE_NAME

# Add this near the top of your app.py, after initializing the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],  # Add your frontend server URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure health check
app.add_middleware(HealthCheckMiddleware, password="", checks={})
logger.info("Added health check middleware")


@app.post("/input_task")
async def input_task_endpoint(input_task: InputTask, request: Request):
    """
    Endpoint to receive the initial input task from the user.

    Args:
        input_task (InputTask): The input task containing the session ID and description.

    Returns:
        dict: Status message, session ID, and plan ID.
    """

    if not rai_success(input_task.description):
        logger.error("RAI failed")

        track_event(
            "RAI failed",
            {
                "status": "Plan not created",
                "description": input_task.description,
                "session_id": input_task.session_id,
            },
        )
 
        return {
            "status": "Plan not created",
        }
    authenticated_user = get_authenticated_user_details(
    request_headers=request.headers
    )
    user_id = authenticated_user["user_principal_id"]

    if not user_id:
        logger.error("No user ID found")

        track_event("UserIdNotFound", {"status_code": 400, "detail": "no user"})

        raise HTTPException(status_code=400, detail="no user")
    if not input_task.session_id:
        input_task.session_id = str(uuid.uuid4())

    # Initialize runtime and context
    logger.info(f"Initializing runtime and context for session {input_task.session_id}")
    runtime, _ = await initialize_runtime_and_context(input_task.session_id,user_id)

    # Send the InputTask message to the GroupChatManager
    group_chat_manager_id = AgentId("group_chat_manager", input_task.session_id)
    logger.info(f"Sending input task to group chat manager: {input_task.session_id}")
    plan: Plan = await runtime.send_message(input_task, group_chat_manager_id)
    
    # Log the result
    logger.info(f"Plan created: {plan.summary}")
    
    # Log custom event for successful input task processing
    track_event(
        "InputTaskProcessed-1",
        {
            "status": f"Plan created:\n {plan.summary}",
            "session_id": input_task.session_id,
            "plan_id": plan.id,
            "description": input_task.description,
        },
    )
    
    return {
        "status": f"Plan created:\n {plan.summary}",
        "session_id": input_task.session_id,
        "plan_id": plan.id,
        "description": input_task.description,
    }


@app.post("/human_feedback")
async def human_feedback_endpoint(human_feedback: HumanFeedback, request: Request):
    """
    Endpoint to receive human feedback on a step.

    Args:
        human_feedback (HumanFeedback): The human feedback message.

        class HumanFeedback(BaseModel):
            step_id: str
            plan_id: str
            session_id: str
            approved: bool
            human_feedback: Optional[str] = None
            updated_action: Optional[str] = None

    Returns:
        dict: Status message and session ID.
    """
    authenticated_user = get_authenticated_user_details(
        request_headers=request.headers
    )
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event("UserIdNotFound", {"status_code": 400, "detail": "no user"})
        raise HTTPException(status_code=400, detail="no user")
    # Initialize runtime and context
    runtime, _ = await initialize_runtime_and_context(human_feedback.session_id, user_id)

    # Send the HumanFeedback message to the HumanAgent
    human_agent_id = AgentId("human_agent", human_feedback.session_id)
    await runtime.send_message(human_feedback, human_agent_id)
    
    track_event(
        "Completed Feedback received",
        {
            "status": "Feedback received",
            "session_id": human_feedback.session_id,
            "step_id": human_feedback.step_id,
        },
    )
    
    return {
        "status": "Feedback received",
        "session_id": human_feedback.session_id,
        "step_id": human_feedback.step_id,
    }


@app.post("/human_clarification_on_plan")
async def human_clarification_endpoint(human_clarification: HumanClarification, request: Request):
    """
    Endpoint to receive human clarification on the plan.

    Args:
        human_clarification (HumanClarification): The human clarification message.

        class HumanFeedback(BaseModel):
            plan_id: str
            session_id: str
            human_clarification: str

    Returns:
        dict: Status message and session ID.
    """
    authenticated_user = get_authenticated_user_details(
        request_headers=request.headers
    )
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event("UserIdNotFound", {"status_code": 400, "detail": "no user"})
        raise HTTPException(status_code=400, detail="no user")
    # Initialize runtime and context
    runtime, _ = await initialize_runtime_and_context(human_clarification.session_id, user_id)

    # Send the HumanFeedback message to the HumanAgent
    planner_agent_id = AgentId("planner_agent", human_clarification.session_id)
    await runtime.send_message(human_clarification, planner_agent_id)
    
    track_event(
        "Completed Human clarification on the plan",
        {
            "status": "Clarification received",
            "session_id": human_clarification.session_id,
        },
    )
    
    return {
        "status": "Clarification received",
        "session_id": human_clarification.session_id,
    }


@app.post("/approve_step_or_steps")
async def approve_step_endpoint(human_feedback: HumanFeedback, request: Request) -> dict[str, str]:
    """
    Endpoint to approve a step if step_id is provided, otherwise approve all the steps.
    """
    authenticated_user = get_authenticated_user_details(
        request_headers=request.headers
    )
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event("UserIdNotFound", {"status_code": 400, "detail": "no user"})
        raise HTTPException(status_code=400, detail="no user")
    # Initialize runtime and context
    runtime, _ = await initialize_runtime_and_context(user_id=user_id)

    # Send the HumanFeedback approval to the GroupChatManager to action

    group_chat_manager_id = AgentId("group_chat_manager", human_feedback.session_id)

    await runtime.send_message(
        human_feedback,
        group_chat_manager_id,
    )
    # Return a status message
    if human_feedback.step_id:
        track_event(
            "Completed Human clarification with step_id",
            {
                "status": f"Step {human_feedback.step_id} - Approval:{human_feedback.approved}."
            },
        )
        
        return {
            "status": f"Step {human_feedback.step_id} - Approval:{human_feedback.approved}."
        }
    else:
        track_event(
            "Completed Human clarification without step_id",
            {
                "status": "All steps approved"
            },
        )
        
        return {"status": "All steps approved"}


@app.get("/plans", response_model=List[PlanWithSteps])
async def get_plans(request: Request, session_id: Optional[str] = Query(None)) -> List[PlanWithSteps]:
    """
    Endpoint to retrieve plans. If session_id is provided, retrieve the plan for that session.
    Otherwise, retrieve all plans.

    Args:
        session_id (Optional[str]): The session ID.

    Returns:
        List[Plan]: The list of plans.
    """
    authenticated_user = get_authenticated_user_details(
        request_headers=request.headers
    )
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event("UserIdNotFound", {"status_code": 400, "detail": "no user"})
        raise HTTPException(status_code=400, detail="no user")
    
    cosmos = CosmosBufferedChatCompletionContext(session_id or "", user_id)

    if session_id:
        plan = await cosmos.get_plan_by_session(session_id=session_id)
        if not plan:
            track_event("GetPlanBySessionNotFound", {"status_code": 400, "detail": "Plan not found"})
            raise HTTPException(status_code=404, detail="Plan not found")

        steps = await cosmos.get_steps_by_plan(plan_id=plan.id)
        plan_with_steps = PlanWithSteps(**plan.model_dump(), steps=steps)
        plan_with_steps.update_step_counts()
        return [plan_with_steps]

    all_plans = await cosmos.get_all_plans()
    # Fetch steps for all plans concurrently
    steps_for_all_plans = await asyncio.gather(
        *[cosmos.get_steps_by_plan(plan_id=plan.id) for plan in all_plans]
    )
    # Create list of PlanWithSteps and update step counts
    list_of_plans_with_steps = []
    for plan, steps in zip(all_plans, steps_for_all_plans):
        plan_with_steps = PlanWithSteps(**plan.model_dump(), steps=steps)
        plan_with_steps.update_step_counts()
        list_of_plans_with_steps.append(plan_with_steps)

    return list_of_plans_with_steps


@app.get("/steps/{plan_id}", response_model=List[Step])
async def get_steps_by_plan(plan_id: str, request: Request) -> List[Step]:
    """
    Endpoint to retrieve steps for a specific plan.

    Args:
        plan_id (str): The plan ID.

    Returns:
        List[Step]: The list of steps.
    """
    authenticated_user = get_authenticated_user_details(
        request_headers=request.headers
    )
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event("UserIdNotFound", {"status_code": 400, "detail": "no user"})
        raise HTTPException(status_code=400, detail="no user")
    cosmos = CosmosBufferedChatCompletionContext("", user_id)
    steps = await cosmos.get_steps_by_plan(plan_id=plan_id)
    return steps


@app.get("/agent_messages/{session_id}", response_model=List[AgentMessage])
async def get_agent_messages(session_id: str, request: Request) -> List[AgentMessage]:
    """
    Endpoint to retrieve agent messages for a specific session.

    Args:
        session_id (str): The session ID.

    Returns:
        List[AgentMessage]: The list of agent messages.
    """
    authenticated_user = get_authenticated_user_details(
        request_headers=request.headers
    )
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event("UserIdNotFound", {"status_code": 400, "detail": "no user"})
        raise HTTPException(status_code=400, detail="no user")
    cosmos = CosmosBufferedChatCompletionContext(session_id, user_id)
    agent_messages = await cosmos.get_data_by_type("agent_message")
    return agent_messages


@app.delete("/messages")
async def delete_all_messages(request: Request) -> dict[str, str]:
    """
    Endpoint to delete all messages across sessions.

    Returns:
        dict: Confirmation of deletion.
    """
    authenticated_user = get_authenticated_user_details(
        request_headers=request.headers
    )
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(status_code=400, detail="no user")
    cosmos = CosmosBufferedChatCompletionContext(session_id="", user_id=user_id)
    logging.info("Deleting all plans")
    await cosmos.delete_all_messages("plan")
    logging.info("Deleting all sessions")
    await cosmos.delete_all_messages("session")
    logging.info("Deleting all steps")
    await cosmos.delete_all_messages("step")
    logging.info("Deleting all agent_messages")
    await cosmos.delete_all_messages("agent_message")
    return {"status": "All messages deleted"}


@app.get("/messages")
async def get_all_messages(request: Request):
    """
    Endpoint to retrieve all messages.

    Returns:
        List[dict]: The list of message dictionaries.
    """
    authenticated_user = get_authenticated_user_details(
        request_headers=request.headers
    )
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(status_code=400, detail="no user")
    cosmos = CosmosBufferedChatCompletionContext(session_id="", user_id=user_id)
    message_list = await cosmos.get_all_messages()
    return message_list


@app.get("/api/agent-tools")
async def get_agent_tools():
    return retrieve_all_agent_tools()


# Serve the frontend from the backend
# app.mount("/", StaticFiles(directory="wwwroot"), name="wwwroot")

# Run the app
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
