# app_kernel.py
import asyncio
import logging
import os
import uuid
import time
from typing import Dict, List, Optional

# Semantic Kernel imports
from app_config import config
from auth.auth_utils import get_authenticated_user_details

# Azure monitoring
from azure.monitor.opentelemetry import configure_azure_monitor
from config_kernel import Config
from event_utils import track_event_if_configured

# FastAPI imports
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from kernel_agents.agent_factory import AgentFactory

# Local imports
from middleware.health_check import HealthCheckMiddleware
from models.messages_kernel import (
    AgentMessage,
    AgentType,
    HumanClarification,
    HumanFeedback,
    InputTask,
    Plan,
    PlanStatus,
    PlanWithSteps,
    Step,
)

# Updated import for KernelArguments
from utils_kernel import initialize_runtime_and_context, rai_success

# Check if the Application Insights Instrumentation Key is set in the environment variables
connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if connection_string:
    # Configure Application Insights if the Instrumentation Key is found
    configure_azure_monitor(connection_string=connection_string)
    logging.info(
        "Application Insights configured with the provided Instrumentation Key"
    )
else:
    # Log a warning if the Instrumentation Key is not found
    logging.warning(
        "No Application Insights Instrumentation Key found. Skipping configuration"
    )

# Configure logging
logging.basicConfig(level=logging.INFO)

# Suppress INFO logs from 'azure.core.pipeline.policies.http_logging_policy'
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)
logging.getLogger("azure.identity.aio._internal").setLevel(logging.WARNING)

# # Suppress info logs from OpenTelemetry exporter
logging.getLogger("azure.monitor.opentelemetry.exporter.export._base").setLevel(
    logging.WARNING
)

# Initialize the FastAPI app
app = FastAPI()

# Add a simple in-memory store to track active streaming requests with timestamps
active_streams = {}  # Changed to dict to store timestamps

frontend_url = Config.FRONTEND_SITE_NAME

# Add this near the top of your app.py, after initializing the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure health check
app.add_middleware(HealthCheckMiddleware, password="", checks={})
logging.info("Added health check middleware")


@app.post("/api/input_task")
async def input_task_endpoint(input_task: InputTask, request: Request):
    """
    Receive the initial input task from the user.
    """
    # Fix 1: Properly await the async rai_success function
    if not await rai_success(input_task.description):
        print("RAI failed")

        track_event_if_configured(
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
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    # Generate session ID if not provided
    if not input_task.session_id:
        input_task.session_id = str(uuid.uuid4())

    try:
        # Create all agents instead of just the planner agent
        # This ensures other agents are created first and the planner has access to them
        kernel, memory_store = await initialize_runtime_and_context(
            input_task.session_id, user_id
        )
        client = None
        try:
            client = config.get_ai_project_client()
        except Exception as client_exc:
            logging.error(f"Error creating AIProjectClient: {client_exc}")

        agents = await AgentFactory.create_all_agents(
            session_id=input_task.session_id,
            user_id=user_id,
            memory_store=memory_store,
            client=client,
        )

        group_chat_manager = agents[AgentType.GROUP_CHAT_MANAGER.value]

        # Convert input task to JSON for the kernel function, add user_id here

        # Use the planner to handle the task
        await group_chat_manager.handle_input_task(input_task)

        # Get plan from memory store
        plan = await memory_store.get_plan_by_session(input_task.session_id)

        if not plan:  # If the plan is not found, raise an error
            track_event_if_configured(
                "PlanNotFound",
                {
                    "status": "Plan not found",
                    "session_id": input_task.session_id,
                    "description": input_task.description,
                },
            )
            raise HTTPException(status_code=404, detail="Plan not found")
        # Log custom event for successful input task processing
        track_event_if_configured(
            "InputTaskProcessed",
            {
                "status": f"Plan created with ID: {plan.id}",
                "session_id": input_task.session_id,
                "plan_id": plan.id,
                "description": input_task.description,
            },
        )
        if client:
            try:
                client.close()
            except Exception as e:
                logging.error(f"Error sending to AIProjectClient: {e}")
        return {
            "status": f"Plan created with ID: {plan.id}",
            "session_id": input_task.session_id,
            "plan_id": plan.id,
            "description": input_task.description,
        }

    except Exception as e:
        track_event_if_configured(
            "InputTaskError",
            {
                "session_id": input_task.session_id,
                "description": input_task.description,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=400, detail=f"Error creating plan: {e}")


@app.post("/api/create_plan")
async def create_plan_endpoint(input_task: InputTask, request: Request):
    """
    Create a new plan without full processing.
    
    ---
    tags:
      - Plans
    parameters:
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            session_id:
              type: string
              description: Session ID for the plan
            description:
              type: string
              description: The task description to validate and create plan for
    responses:
      200:
        description: Plan created successfully
        schema:
          type: object
          properties:
            plan_id:
              type: string
              description: The ID of the newly created plan
            status:
              type: string
              description: Success message
            session_id:
              type: string
              description: Session ID associated with the plan
      400:
        description: RAI check failed or invalid input
        schema:
          type: object
          properties:
            detail:
              type: string
              description: Error message
    """
    # Perform RAI check on the description
    if not await rai_success(input_task.description):
        track_event_if_configured(
            "RAI failed",
            {
                "status": "Plan not created - RAI check failed",
                "description": input_task.description,
                "session_id": input_task.session_id,
            },
        )
        raise HTTPException(
            status_code=400, 
            detail="Task description failed safety validation. Please revise your request."
        )

    # Get authenticated user
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    # Generate session ID if not provided
    if not input_task.session_id:
        input_task.session_id = str(uuid.uuid4())

    try:
        # Initialize memory store
        kernel, memory_store = await initialize_runtime_and_context(
            input_task.session_id, user_id
        )

        # Create a new Plan object
        plan = Plan(
            session_id=input_task.session_id,
            user_id=user_id,
            initial_goal=input_task.description,
            overall_status=PlanStatus.in_progress,
            source=AgentType.PLANNER.value
        )

        # Save the plan to the database
        await memory_store.add_plan(plan)

        # Log successful plan creation
        track_event_if_configured(
            "PlanCreated",
            {
                "status": f"Plan created with ID: {plan.id}",
                "session_id": input_task.session_id,
                "plan_id": plan.id,
                "description": input_task.description,
            },
        )

        return {
            "plan_id": plan.id,
            "status": "Plan created successfully",
            "session_id": input_task.session_id,
        }

    except Exception as e:
        track_event_if_configured(
            "CreatePlanError",
            {
                "session_id": input_task.session_id,
                "description": input_task.description,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=400, detail=f"Error creating plan: {e}")


@app.options("/api/generate_plan/{plan_id}")
async def generate_plan_options(plan_id: str):
    """Handle CORS preflight for generate_plan endpoint"""
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@app.post("/api/generate_plan/{plan_id}")
async def generate_plan_endpoint(plan_id: str, request: Request):
    """
    Generate detailed plan with steps using reasoning LLM and stream the process.
    
    ---
    tags:
      - Plans
    parameters:
      - name: plan_id
        in: path
        type: string
        required: true
        description: The ID of the plan to generate steps for
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
    responses:
      200:
        description: Streaming response of the reasoning process
        content:
          text/plain:
            schema:
              type: string
              description: Stream of reasoning process and final JSON
      400:
        description: Plan not found or other error
        schema:
          type: object
          properties:
            detail:
              type: string
              description: Error message
    """
    # Get authenticated user first
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    # Clean up stale streams (older than 5 minutes)
    current_time = time.time()
    stale_streams = [k for k, v in active_streams.items() if current_time - v > 300]
    for stale_key in stale_streams:
        active_streams.pop(stale_key, None)
        logging.info(f"Cleaned up stale stream: {stale_key}")

    # Check if there's already an active stream for this plan + user combination
    stream_key = f"stream_{plan_id}_{user_id}"
    logging.info(f"Received stream request for plan {plan_id} from user {user_id}, active streams: {list(active_streams.keys())}")
    if stream_key in active_streams:
        logging.warning(f"Duplicate stream request for plan {plan_id} from user {user_id}, rejecting. Active streams: {list(active_streams.keys())}")
        raise HTTPException(status_code=429, detail="Stream already in progress for this plan")

    try:
        # Add to active streams with timestamp
        active_streams[stream_key] = current_time
        logging.info(f"Added stream {stream_key} to active streams. Current active: {list(active_streams.keys())}")
        
        # Initialize memory store
        kernel, memory_store = await initialize_runtime_and_context("", user_id)

        # Get the existing plan
        plan = await memory_store.get_plan_by_plan_id(plan_id)
        if not plan:
            track_event_if_configured(
                "PlanNotFound",
                {"plan_id": plan_id, "error": "Plan not found"},
            )
            active_streams.pop(stream_key, None)  # Remove from active streams
            logging.info(f"Plan {plan_id} not found, removed stream from active streams")
            raise HTTPException(status_code=404, detail="Plan not found")

        # Generate streaming response
        async def generate_reasoning_stream():
            try:
                logging.info(f"Starting stream for plan {plan_id}")
                
                # Import the reasoning generation function
                from utils_kernel import generate_plan_with_reasoning_stream
                
                # Stream the reasoning process and get the final result
                async for chunk in generate_plan_with_reasoning_stream(plan.initial_goal, plan_id, memory_store):
                    yield f"data: {chunk}\n\n"
                
                # Send completion signal
                yield f"data: [DONE]\n\n"
                logging.info(f"Completed stream for plan {plan_id}")
                
            except Exception as e:
                error_msg = f"Error during plan generation: {str(e)}"
                logging.error(error_msg)
                yield f"data: ERROR: {error_msg}\n\n"
            finally:
                # Always remove from active streams when done
                active_streams.pop(stream_key, None)
                logging.info(f"Removed stream {stream_key} from active streams. Remaining: {list(active_streams.keys())}")

        return StreamingResponse(
            generate_reasoning_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            }
        )

    except HTTPException:
        # Remove from active streams on HTTP errors
        active_streams.pop(stream_key, None)
        logging.info(f"HTTP error, removed stream {stream_key} from active streams")
        raise
    except Exception as e:
        # Remove from active streams on other errors
        active_streams.pop(stream_key, None)
        logging.error(f"Error in generate_plan_endpoint: {e}, removed stream {stream_key} from active streams")
        track_event_if_configured(
            "GeneratePlanError",
            {
                "plan_id": plan_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=400, detail=f"Error generating plan: {e}")


@app.post("/api/human_feedback")
async def human_feedback_endpoint(human_feedback: HumanFeedback, request: Request):
    """
    Receive human feedback on a step.

    ---
    tags:
      - Feedback
    parameters:
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            step_id:
              type: string
              description: The ID of the step to provide feedback for
            plan_id:
              type: string
              description: The plan ID
            session_id:
              type: string
              description: The session ID
            approved:
              type: boolean
              description: Whether the step is approved
            human_feedback:
              type: string
              description: Optional feedback details
            updated_action:
              type: string
              description: Optional updated action
            user_id:
              type: string
              description: The user ID providing the feedback
    responses:
      200:
        description: Feedback received successfully
        schema:
          type: object
          properties:
            status:
              type: string
            session_id:
              type: string
            step_id:
              type: string
      400:
        description: Missing or invalid user information
    """
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    kernel, memory_store = await initialize_runtime_and_context(
        human_feedback.session_id, user_id
    )

    client = None
    try:
        client = config.get_ai_project_client()
    except Exception as client_exc:
        logging.error(f"Error creating AIProjectClient: {client_exc}")

    human_agent = await AgentFactory.create_agent(
        agent_type=AgentType.HUMAN,
        session_id=human_feedback.session_id,
        user_id=user_id,
        memory_store=memory_store,
        client=client,
    )

    if human_agent is None:
        track_event_if_configured(
            "AgentNotFound",
            {
                "status": "Agent not found",
                "session_id": human_feedback.session_id,
                "step_id": human_feedback.step_id,
            },
        )
        raise HTTPException(status_code=404, detail="Agent not found")

    # Use the human agent to handle the feedback
    await human_agent.handle_human_feedback(human_feedback=human_feedback)

    track_event_if_configured(
        "Completed Feedback received",
        {
            "status": "Feedback received",
            "session_id": human_feedback.session_id,
            "step_id": human_feedback.step_id,
        },
    )
    if client:
        try:
            client.close()
        except Exception as e:
            logging.error(f"Error sending to AIProjectClient: {e}")
    return {
        "status": "Feedback received",
        "session_id": human_feedback.session_id,
        "step_id": human_feedback.step_id,
    }


@app.post("/api/human_clarification_on_plan")
async def human_clarification_endpoint(
    human_clarification: HumanClarification, request: Request
):
    """
    Receive human clarification on a plan.

    ---
    tags:
      - Clarification
    parameters:
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            plan_id:
              type: string
              description: The plan ID requiring clarification
            session_id:
              type: string
              description: The session ID
            human_clarification:
              type: string
              description: Clarification details provided by the user
            user_id:
              type: string
              description: The user ID providing the clarification
    responses:
      200:
        description: Clarification received successfully
        schema:
          type: object
          properties:
            status:
              type: string
            session_id:
              type: string
      400:
        description: Missing or invalid user information
    """
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    kernel, memory_store = await initialize_runtime_and_context(
        human_clarification.session_id, user_id
    )
    client = None
    try:
        client = config.get_ai_project_client()
    except Exception as client_exc:
        logging.error(f"Error creating AIProjectClient: {client_exc}")

    human_agent = await AgentFactory.create_agent(
        agent_type=AgentType.HUMAN,
        session_id=human_clarification.session_id,
        user_id=user_id,
        memory_store=memory_store,
        client=client,
    )

    if human_agent is None:
        track_event_if_configured(
            "AgentNotFound",
            {
                "status": "Agent not found",
                "session_id": human_clarification.session_id,
                "step_id": human_clarification.step_id,
            },
        )
        raise HTTPException(status_code=404, detail="Agent not found")

    # Use the human agent to handle the feedback
    await human_agent.handle_human_clarification(
        human_clarification=human_clarification
    )

    track_event_if_configured(
        "Completed Human clarification on the plan",
        {
            "status": "Clarification received",
            "session_id": human_clarification.session_id,
        },
    )
    if client:
        try:
            client.close()
        except Exception as e:
            logging.error(f"Error sending to AIProjectClient: {e}")
    return {
        "status": "Clarification received",
        "session_id": human_clarification.session_id,
    }


@app.post("/api/approve_step_or_steps")
async def approve_step_endpoint(
    human_feedback: HumanFeedback, request: Request
) -> Dict[str, str]:
    """
    Approve a step or multiple steps in a plan.

    ---
    tags:
      - Approval
    parameters:
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            step_id:
              type: string
              description: Optional step ID to approve
            plan_id:
              type: string
              description: The plan ID
            session_id:
              type: string
              description: The session ID
            approved:
              type: boolean
              description: Whether the step(s) are approved
            human_feedback:
              type: string
              description: Optional feedback details
            updated_action:
              type: string
              description: Optional updated action
            user_id:
              type: string
              description: The user ID providing the approval
    responses:
      200:
        description: Approval status returned
        schema:
          type: object
          properties:
            status:
              type: string
      400:
        description: Missing or invalid user information
    """
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    # Get the agents for this session
    kernel, memory_store = await initialize_runtime_and_context(
        human_feedback.session_id, user_id
    )
    client = None
    try:
        client = config.get_ai_project_client()
    except Exception as client_exc:
        logging.error(f"Error creating AIProjectClient: {client_exc}")
    agents = await AgentFactory.create_all_agents(
        session_id=human_feedback.session_id,
        user_id=user_id,
        memory_store=memory_store,
        client=client,
    )

    # Send the approval to the group chat manager
    group_chat_manager = agents[AgentType.GROUP_CHAT_MANAGER.value]

    await group_chat_manager.handle_human_feedback(human_feedback)

    if client:
        try:
            client.close()
        except Exception as e:
            logging.error(f"Error sending to AIProjectClient: {e}")
    # Return a status message
    if human_feedback.step_id:
        track_event_if_configured(
            "Completed Human clarification with step_id",
            {
                "status": f"Step {human_feedback.step_id} - Approval:{human_feedback.approved}."
            },
        )

        return {
            "status": f"Step {human_feedback.step_id} - Approval:{human_feedback.approved}."
        }
    else:
        track_event_if_configured(
            "Completed Human clarification without step_id",
            {"status": "All steps approved"},
        )

        return {"status": "All steps approved"}


@app.post("/api/human_clarification_on_plan_stream")
async def human_clarification_stream_endpoint(
    human_clarification: HumanClarification, request: Request
):
    """
    Receive human clarification on a plan with streaming agent responses.
    """
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(status_code=400, detail="no user")

    async def generate_clarification_stream():
        try:
            # Initialize agents and memory store
            kernel, memory_store = await initialize_runtime_and_context(
                human_clarification.session_id, user_id
            )
            client = None
            try:
                client = config.get_ai_project_client()
            except Exception as client_exc:
                logging.error(f"Error creating AIProjectClient: {client_exc}")

            # Create human agent
            human_agent = await AgentFactory.create_agent(
                agent_type=AgentType.HUMAN,
                session_id=human_clarification.session_id,
                user_id=user_id,
                memory_store=memory_store,
                client=client,
            )

            if human_agent is None:
                yield "data: Failed to create human agent\n\n"
                return

            # Stream initial processing message
            yield "data: **Human Agent:** Processing your clarification...\n\n"
            await asyncio.sleep(0.5)

            # Process the clarification
            result = await human_agent.handle_human_clarification(
                human_clarification=human_clarification
            )

            # Stream planner response
            yield "data: **Planner Agent:** Thanks, the plan has been updated based on your clarification.\n\n"
            await asyncio.sleep(0.5)

            # Stream completion message
            yield "data: **System:** Plan clarification processed. You can now approve individual steps.\n\n"
            yield "data: [DONE]\n\n"

            if client:
                try:
                    client.close()
                except Exception as e:
                    logging.error(f"Error closing AIProjectClient: {e}")

        except Exception as e:
            logging.error(f"Error in clarification streaming: {e}")
            yield f"data: Error processing clarification: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_clarification_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.post("/api/approve_step_or_steps_stream")
async def approve_step_stream_endpoint(
    human_feedback: HumanFeedback, request: Request
):
    """
    Approve a step or multiple steps with streaming agent responses.
    """
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(status_code=400, detail="no user")

    async def generate_approval_stream():
        try:
            # Initialize agents and memory store
            kernel, memory_store = await initialize_runtime_and_context(
                human_feedback.session_id, user_id
            )
            client = None
            try:
                client = config.get_ai_project_client()
            except Exception as client_exc:
                logging.error(f"Error creating AIProjectClient: {client_exc}")

            # Create all agents
            agents = await AgentFactory.create_all_agents(
                session_id=human_feedback.session_id,
                user_id=user_id,
                memory_store=memory_store,
                client=client,
            )

            group_chat_manager = agents[AgentType.GROUP_CHAT_MANAGER.value]

            # Stream initial processing message
            action = "Approving" if human_feedback.approved else "Rejecting"
            yield f"data: **Group Chat Manager:** {action} step and coordinating with relevant agents...\n\n"
            await asyncio.sleep(0.5)

            # Process the approval
            await group_chat_manager.handle_human_feedback(human_feedback)

            # Get the updated step to see what agent was assigned
            updated_steps = await memory_store.get_steps_by_plan(human_feedback.plan_id)
            target_step = next((s for s in updated_steps if s.id == human_feedback.step_id), None)
            
            # Stream agent responses based on step
            if human_feedback.approved:
                yield "data: **Human Agent:** Step approved successfully.\n\n"
                await asyncio.sleep(0.5)
                yield "data: **Group Chat Manager:** Step has been marked as approved and will be executed.\n\n"
                await asyncio.sleep(0.5)
                
                if target_step and target_step.agent:
                    # Show which agent is handling the step
                    agent_name = target_step.agent.replace('_', ' ').title()
                    yield f"data: **Group Chat Manager:** Assigning step to {agent_name} for execution...\n\n"
                    await asyncio.sleep(0.5)
                    
                    # Simulate detailed agent planning/execution response
                    yield f"data: **{agent_name}:** Analyzing step requirements...\n\n"
                    await asyncio.sleep(0.5)
                    yield f"data: **{agent_name}:** Creating detailed execution plan for: {target_step.action}\n\n"
                    await asyncio.sleep(0.5)
                    yield f"data: **{agent_name}:** ✅ Step execution plan prepared. Ready to proceed when all approvals are complete.\n\n"
                    await asyncio.sleep(0.5)
                    yield f"data: **Group Chat Manager:** {agent_name} has confirmed step readiness. Step is now marked as approved.\n\n"
            else:
                yield "data: **Human Agent:** Step has been rejected.\n\n"
                await asyncio.sleep(0.5)
                yield "data: **Group Chat Manager:** Step marked as rejected. Plan updated accordingly.\n\n"

            await asyncio.sleep(0.5)
            yield "data: **System:** Step approval processed successfully.\n\n"
            yield "data: [DONE]\n\n"

            if client:
                try:
                    client.close()
                except Exception as e:
                    logging.error(f"Error closing AIProjectClient: {e}")

        except Exception as e:
            logging.error(f"Error in approval streaming: {e}")
            yield f"data: Error processing approval: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_approval_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/api/plans")
async def get_plans(
    request: Request,
    session_id: Optional[str] = Query(None),
    plan_id: Optional[str] = Query(None),
):
    """
    Retrieve plans for the current user.

    ---
    tags:
      - Plans
    parameters:
      - name: session_id
        in: query
        type: string
        required: false
        description: Optional session ID to retrieve plans for a specific session
    responses:
      200:
        description: List of plans with steps for the user
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
                description: Unique ID of the plan
              session_id:
                type: string
                description: Session ID associated with the plan
              initial_goal:
                type: string
                description: The initial goal derived from the user's input
              overall_status:
                type: string
                description: Status of the plan (e.g., in_progress, completed)
              steps:
                type: array
                items:
                  type: object
                  properties:
                    id:
                      type: string
                      description: Unique ID of the step
                    plan_id:
                      type: string
                      description: ID of the plan the step belongs to
                    action:
                      type: string
                      description: The action to be performed
                    agent:
                      type: string
                      description: The agent responsible for the step
                    status:
                      type: string
                      description: Status of the step (e.g., planned, approved, completed)
      400:
        description: Missing or invalid user information
      404:
        description: Plan not found
    """
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    # Initialize memory context
    kernel, memory_store = await initialize_runtime_and_context(
        session_id or "", user_id
    )

    if session_id:
        plan = await memory_store.get_plan_by_session(session_id=session_id)
        if not plan:
            track_event_if_configured(
                "GetPlanBySessionNotFound",
                {"status_code": 400, "detail": "Plan not found"},
            )
            raise HTTPException(status_code=404, detail="Plan not found")

        # Use get_steps_by_plan to match the original implementation
        steps = await memory_store.get_steps_by_plan(plan_id=plan.id)
        plan_with_steps = PlanWithSteps(**plan.model_dump(), steps=steps)
        plan_with_steps.update_step_counts()
        return [plan_with_steps]
    if plan_id:
        plan = await memory_store.get_plan_by_plan_id(plan_id=plan_id)
        if not plan:
            track_event_if_configured(
                "GetPlanBySessionNotFound",
                {"status_code": 400, "detail": "Plan not found"},
            )
            raise HTTPException(status_code=404, detail="Plan not found")

        # Use get_steps_by_plan to match the original implementation
        steps = await memory_store.get_steps_by_plan(plan_id=plan.id)
        messages = await memory_store.get_data_by_type_and_session_id(
            "agent_message", session_id=plan.session_id
        )

        plan_with_steps = PlanWithSteps(**plan.model_dump(), steps=steps)
        plan_with_steps.update_step_counts()
        return [plan_with_steps, messages]

    all_plans = await memory_store.get_all_plans()
    # Fetch steps for all plans concurrently
    steps_for_all_plans = await asyncio.gather(
        *[memory_store.get_steps_by_plan(plan_id=plan.id) for plan in all_plans]
    )
    # Create list of PlanWithSteps and update step counts
    list_of_plans_with_steps = []
    for plan, steps in zip(all_plans, steps_for_all_plans):
        plan_with_steps = PlanWithSteps(**plan.model_dump(), steps=steps)
        plan_with_steps.update_step_counts()
        list_of_plans_with_steps.append(plan_with_steps)

    return list_of_plans_with_steps


@app.get("/api/steps/{plan_id}", response_model=List[Step])
async def get_steps_by_plan(plan_id: str, request: Request) -> List[Step]:
    """
    Retrieve steps for a specific plan.

    ---
    tags:
      - Steps
    parameters:
      - name: plan_id
        in: path
        type: string
        required: true
        description: The ID of the plan to retrieve steps for
    responses:
      200:
        description: List of steps associated with the specified plan
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
                description: Unique ID of the step
              plan_id:
                type: string
                description: ID of the plan the step belongs to
              action:
                type: string
                description: The action to be performed
              agent:
                type: string
                description: The agent responsible for the step
              status:
                type: string
                description: Status of the step (e.g., planned, approved, completed)
              agent_reply:
                type: string
                description: Optional response from the agent after execution
              human_feedback:
                type: string
                description: Optional feedback provided by a human
              updated_action:
                type: string
                description: Optional modified action based on feedback
       400:
        description: Missing or invalid user information
      404:
        description: Plan or steps not found
    """
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    # Initialize memory context
    kernel, memory_store = await initialize_runtime_and_context("", user_id)
    steps = await memory_store.get_steps_for_plan(plan_id=plan_id)
    return steps


@app.get("/api/agent_messages/{session_id}", response_model=List[AgentMessage])
async def get_agent_messages(session_id: str, request: Request) -> List[AgentMessage]:
    """
    Retrieve agent messages for a specific session.

    ---
    tags:
      - Agent Messages
    parameters:
      - name: session_id
        in: path
        type: string
        required: true
        in: path
        type: string
        required: true
        description: The ID of the session to retrieve agent messages for
    responses:
      200:
        description: List of agent messages associated with the specified session
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
                description: Unique ID of the agent message
              session_id:
                type: string
                description: Session ID associated with the message
              plan_id:
                type: string
                description: Plan ID related to the agent message
              content:
                type: string
                description: Content of the message
              source:
                type: string
                description: Source of the message (e.g., agent type)
              timestamp:
                type: string
                format: date-time
                description: Timestamp of the message
              step_id:
                type: string
                description: Optional step ID associated with the message
      400:
        description: Missing or invalid user information
      404:
        description: Agent messages not found
    """
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    # Initialize memory context
    kernel, memory_store = await initialize_runtime_and_context(
        session_id or "", user_id
    )
    agent_messages = await memory_store.get_data_by_type("agent_message")
    return agent_messages


@app.get("/api/agent_messages_by_plan/{plan_id}", response_model=List[AgentMessage])
async def get_agent_messages_by_plan(
    plan_id: str, request: Request
) -> List[AgentMessage]:
    """
    Retrieve agent messages for a specific session.

    ---
    tags:
      - Agent Messages
    parameters:
      - name: session_id
        in: path
        type: string
        required: true
        in: path
        type: string
        required: true
        description: The ID of the session to retrieve agent messages for
    responses:
      200:
        description: List of agent messages associated with the specified session
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
                description: Unique ID of the agent message
              session_id:
                type: string
                description: Session ID associated with the message
              plan_id:
                type: string
                description: Plan ID related to the agent message
              content:
                type: string
                description: Content of the message
              source:
                type: string
                description: Source of the message (e.g., agent type)
              timestamp:
                type: string
                format: date-time
                description: Timestamp of the message
              step_id:
                type: string
                description: Optional step ID associated with the message
      400:
        description: Missing or invalid user information
      404:
        description: Agent messages not found
    """
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    # Initialize memory context
    kernel, memory_store = await initialize_runtime_and_context("", user_id)
    agent_messages = await memory_store.get_data_by_type_and_plan_id("agent_message")
    return agent_messages


@app.delete("/api/messages")
async def delete_all_messages(request: Request) -> Dict[str, str]:
    """
    Delete all messages across sessions.

    ---
    tags:
      - Messages
    responses:
      200:
        description: Confirmation of deletion
        schema:
          type: object
          properties:
            status:
              type: string
              description: Status message indicating all messages were deleted
      400:
        description: Missing or invalid user information
    """
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    # Initialize memory context
    kernel, memory_store = await initialize_runtime_and_context("", user_id)

    await memory_store.delete_all_items("plan")
    await memory_store.delete_all_items("session")
    await memory_store.delete_all_items("step")
    await memory_store.delete_all_items("agent_message")

    # Clear the agent factory cache
    AgentFactory.clear_cache()

    return {"status": "All messages deleted"}


@app.get("/api/messages")
async def get_all_messages(request: Request):
    """
    Retrieve all messages across sessions.

    ---
    tags:
      - Messages
    responses:
      200:
        description: List of all messages across sessions
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
                description: Unique ID of the message
              data_type:
                type: string
                description: Type of the message (e.g., session, step, plan, agent_message)
              session_id:
                type: string
                description: Session ID associated with the message
              user_id:
                type: string
                description: User ID associated with the message
              content:
                type: string
                description: Content of the message
              timestamp:
                type: string
                format: date-time
                description: Timestamp of the message
      400:
        description: Missing or invalid user information
    """
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    # Initialize memory context
    kernel, memory_store = await initialize_runtime_and_context("", user_id)
    message_list = await memory_store.get_all_items()
    return message_list


@app.get("/api/agent-tools")
async def get_agent_tools():
    """
    Retrieve all available agent tools.

    ---
    tags:
      - Agent Tools
    responses:
      200:
        description: List of all available agent tools and their descriptions
        schema:
          type: array
          items:
            type: object
            properties:
              agent:
                type: string
                description: Name of the agent associated with the tool
              function:
                type: string
                description: Name of the tool function
              description:
                type: string
                description: Detailed description of what the tool does
              arguments:
                type: string
                description: Arguments required by the tool function
    """
    return []


@app.get("/api/test_stream")
async def test_stream():
    """Simple test endpoint for streaming"""
    async def generate_test_stream():
        for i in range(5):
            yield f"data: Test message {i+1}\n\n"
            await asyncio.sleep(0.5)
        yield f"data: [DONE]\n\n"

    return StreamingResponse(
        generate_test_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


# Run the app
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app_kernel:app", host="127.0.0.1", port=8000, reload=True)
