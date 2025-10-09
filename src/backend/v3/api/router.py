import asyncio
import json
import logging
import uuid
from typing import Optional

import v3.models.messages as messages
from auth.auth_utils import get_authenticated_user_details
from common.database.database_factory import DatabaseFactory
from common.models.messages_kernel import (
    InputTask,
    Plan,
    PlanStatus,
    TeamSelectionRequest,
)
from common.utils.event_utils import track_event_if_configured
from common.utils.utils_kernel import rai_success, rai_validate_team_config
from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from v3.common.services.plan_service import PlanService
from v3.common.services.team_service import TeamService
from v3.config.settings import (
    connection_config,
    orchestration_config,
    team_config,
)
from v3.orchestration.orchestration_manager import OrchestrationManager

router = APIRouter()
logger = logging.getLogger(__name__)

app_v3 = APIRouter(
    prefix="/api/v3",
    responses={404: {"description": "Not found"}},
)


@app_v3.websocket("/socket/{process_id}")
async def start_comms(
    websocket: WebSocket, process_id: str, user_id: str = Query(None)
):
    """Web-Socket endpoint for real-time process status updates."""

    # Always accept the WebSocket connection first
    await websocket.accept()

    user_id = user_id or "00000000-0000-0000-0000-000000000000"

    # Add to the connection manager for backend updates
    connection_config.add_connection(
        process_id=process_id, connection=websocket, user_id=user_id
    )
    track_event_if_configured(
        "WebSocketConnectionAccepted", {"process_id": process_id, "user_id": user_id}
    )

    # Keep the connection open - FastAPI will close the connection if this returns
    try:
        # Keep the connection open - FastAPI will close the connection if this returns
        while True:
            # no expectation that we will receive anything from the client but this keeps
            # the connection open and does not take cpu cycle
            try:
                message = await websocket.receive_text()
                logging.debug(f"Received WebSocket message from {user_id}: {message}")
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                track_event_if_configured(
                    "WebSocketDisconnect",
                    {"process_id": process_id, "user_id": user_id},
                )
                logging.info(f"Client disconnected from batch {process_id}")
                break
    except Exception as e:
        # Fixed logging syntax - removed the error= parameter
        logging.error(f"Error in WebSocket connection: {str(e)}")
    finally:
        # Always clean up the connection
        await connection_config.close_connection(process_id=process_id)


@app_v3.get("/init_team")
async def init_team(
    request: Request,
    team_switched: bool = Query(False),
):  # add team_switched: bool parameter
    """Initialize the user's current team of agents"""

    # Need to store this user state in cosmos db, retrieve it here, and initialize the team
    # current in-memory store is in team_config from settings.py
    # For now I will set the initial install team ids as 00000000-0000-0000-0000-000000000001 (HR),
    # 00000000-0000-0000-0000-000000000002 (Marketing), and 00000000-0000-0000-0000-000000000003 (Retail),
    # and use this value to initialize to HR each time.
    init_team_id = "00000000-0000-0000-0000-000000000001"
    print(f"Init team called, team_switched={team_switched}")
    try:
        authenticated_user = get_authenticated_user_details(
            request_headers=request.headers
        )
        user_id = authenticated_user["user_principal_id"]
        if not user_id:
            track_event_if_configured(
                "UserIdNotFound", {"status_code": 400, "detail": "no user"}
            )
            raise HTTPException(status_code=400, detail="no user")

        # Initialize memory store and service
        memory_store = await DatabaseFactory.get_database(user_id=user_id)
        team_service = TeamService(memory_store)
        user_current_team = await memory_store.get_current_team(user_id=user_id)
        if not user_current_team:
            print("User has no current team, setting to default:", init_team_id)
            user_current_team = await team_service.handle_team_selection(
                user_id=user_id, team_id=init_team_id
            )
            if user_current_team:
                init_team_id = user_current_team.team_id
        else:
            init_team_id = user_current_team.team_id
        # Verify the team exists and user has access to it
        team_configuration = await team_service.get_team_configuration(
            init_team_id, user_id
        )
        if team_configuration is None:
            raise HTTPException(
                status_code=404,
                detail=f"Team configuration '{init_team_id}' not found or access denied",
            )

        # Set as current team in memory
        team_config.set_current_team(
            user_id=user_id, team_configuration=team_configuration
        )

        # Initialize agent team for this user session
        await OrchestrationManager.get_current_or_new_orchestration(
            user_id=user_id, team_config=team_configuration, team_switched=team_switched
        )

        return {
            "status": "Request started successfully",
            "team_id": init_team_id,
            "team": team_configuration,
        }

    except Exception as e:
        track_event_if_configured(
            "InitTeamFailed",
            {
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=400, detail=f"Error starting request: {e}"
        ) from e


@app_v3.post("/process_request")
async def process_request(
    background_tasks: BackgroundTasks, input_task: InputTask, request: Request
):
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
            detail="Request contains content that doesn't meet our safety guidelines, try again.",
        )

    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user found")

    # if not input_task.team_id:
    #     track_event_if_configured(
    #         "TeamIDNofound", {"status_code": 400, "detail": "no team id"}
    #     )
    #     raise HTTPException(status_code=400, detail="no team id")

    if not input_task.session_id:
        input_task.session_id = str(uuid.uuid4())
    try:
        plan_id = str(uuid.uuid4())
        # Initialize memory store and service
        memory_store = await DatabaseFactory.get_database(user_id=user_id)
        user_current_team = await memory_store.get_current_team(user_id=user_id)
        team_id = None
        if user_current_team:
            team_id = user_current_team.team_id
        team = await memory_store.get_team_by_id(team_id=team_id)
        if not team:
            raise HTTPException(
                status_code=404,
                detail=f"Team configuration '{team_id}' not found or access denied",
            )
        plan = Plan(
            id=plan_id,
            plan_id=plan_id,
            user_id=user_id,
            session_id=input_task.session_id,
            team_id=team_id,
            initial_goal=input_task.description,
            overall_status=PlanStatus.in_progress,
        )
        await memory_store.add_plan(plan)

        track_event_if_configured(
            "PlanCreated",
            {
                "status": "success",
                "plan_id": plan.plan_id,
                "session_id": input_task.session_id,
                "user_id": user_id,
                "team_id": team_id,
                "description": input_task.description,
            },
        )
    except Exception as e:
        print(f"Error creating plan: {e}")
        track_event_if_configured(
            "PlanCreationFailed",
            {
                "status": "error",
                "description": input_task.description,
                "session_id": input_task.session_id,
                "user_id": user_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail="Failed to create plan")

    try:
        # background_tasks.add_task(
        #     lambda: current_context.run(lambda:OrchestrationManager().run_orchestration, user_id, input_task)
        # )

        async def run_orchestration_task():
            await OrchestrationManager().run_orchestration(user_id, input_task)

        background_tasks.add_task(run_orchestration_task)

        return {
            "status": "Request started successfully",
            "session_id": input_task.session_id,
            "plan_id": plan_id,
        }

    except Exception as e:
        track_event_if_configured(
            "RequestStartFailed",
            {
                "session_id": input_task.session_id,
                "description": input_task.description,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=400, detail=f"Error starting request: {e}"
        ) from e


@app_v3.post("/plan_approval")
async def plan_approval(
    human_feedback: messages.PlanApprovalResponse, request: Request
):
    """
    Endpoint to receive plan approval or rejection from the user.

    ---
    tags:
      - Plans
    parameters:
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
    requestBody:
      description: Plan approval payload
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              m_plan_id:
                type: string
                description: The internal m_plan id for the plan (required)
              approved:
                type: boolean
                description: Whether the plan is approved (true) or rejected (false)
              feedback:
                type: string
                description: Optional feedback or comment from the user
              plan_id:
                type: string
                description: Optional user-facing plan_id
    responses:
      200:
        description: Approval recorded successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
      401:
        description: Missing or invalid user information
      404:
        description: No active plan found for approval
      500:
        description: Internal server error
    """

    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(
            status_code=401, detail="Missing or invalid user information"
        )
    # Set the approval in the orchestration config
    try:
        if user_id and human_feedback.m_plan_id:
            if (
                orchestration_config
                and human_feedback.m_plan_id in orchestration_config.approvals
            ):
                orchestration_config.approvals[human_feedback.m_plan_id] = (
                    human_feedback.approved
                )
                # orchestration_config.plans[human_feedback.m_plan_id][
                #     "plan_id"
                # ] = human_feedback.plan_id
                print("Plan approval received:", human_feedback)
                # print(
                #     "Updated orchestration config:",
                #     orchestration_config.plans[human_feedback.m_plan_id],
                # )
                try:
                    result = await PlanService.handle_plan_approval(
                        human_feedback, user_id
                    )
                    print("Plan approval processed:", result)
                except ValueError as ve:
                    print(f"ValueError processing plan approval: {ve}")
                except Exception as e:
                    print(f"Error processing plan approval: {e}")
                track_event_if_configured(
                    "PlanApprovalReceived",
                    {
                        "plan_id": human_feedback.plan_id,
                        "m_plan_id": human_feedback.m_plan_id,
                        "approved": human_feedback.approved,
                        "user_id": user_id,
                        "feedback": human_feedback.feedback,
                    },
                )

                return {"status": "approval recorded"}
            else:
                logging.warning(
                    f"No orchestration or plan found for plan_id: {human_feedback.m_plan_id}"
                )
                raise HTTPException(
                    status_code=404, detail="No active plan found for approval"
                )
    except Exception as e:
        logging.error(f"Error processing plan approval: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app_v3.post("/user_clarification")
async def user_clarification(
    human_feedback: messages.UserClarificationResponse, request: Request
):
    """
    Endpoint to receive user clarification responses for clarification requests sent by the system.

    ---
    tags:
      - Plans
    parameters:
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
    requestBody:
      description: User clarification payload
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              request_id:
                type: string
                description: The clarification request id sent by the system (required)
              answer:
                type: string
                description: The user's answer or clarification text
              plan_id:
                type: string
                description: (Optional) Associated plan_id
              m_plan_id:
                type: string
                description: (Optional) Internal m_plan id
    responses:
      200:
        description: Clarification recorded successfully
      400:
        description: RAI check failed or invalid input
      401:
        description: Missing or invalid user information
      404:
        description: No active plan found for clarification
      500:
        description: Internal server error
    """

    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(
            status_code=401, detail="Missing or invalid user information"
        )
    # Set the approval in the orchestration config
    if user_id and human_feedback.request_id:
        # validate rai
        if human_feedback.answer is not None or human_feedback.answer != "":
            if not await rai_success(human_feedback.answer):
                track_event_if_configured(
                    "RAI failed",
                    {
                        "status": "Plan Clarification ",
                        "description": human_feedback.answer,
                        "request_id": human_feedback.request_id,
                    },
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_type": "RAI_VALIDATION_FAILED",
                        "message": "Content Safety Check Failed",
                        "description": "Your request contains content that doesn't meet our safety guidelines. Please modify your request to ensure it's appropriate and try again.",
                        "suggestions": [
                            "Remove any potentially harmful, inappropriate, or unsafe content",
                            "Use more professional and constructive language",
                            "Focus on legitimate business or educational objectives",
                            "Ensure your request complies with content policies",
                        ],
                        "user_action": "Please revise your request and try again",
                    },
                )

        if (
            orchestration_config
            and human_feedback.request_id in orchestration_config.clarifications
        ):
            orchestration_config.clarifications[human_feedback.request_id] = (
                human_feedback.answer
            )

            try:
                result = await PlanService.handle_human_clarification(
                    human_feedback, user_id
                )
                print("Human clarification processed:", result)
            except ValueError as ve:
                print(f"ValueError processing human clarification: {ve}")
            except Exception as e:
                print(f"Error processing human clarification: {e}")
            track_event_if_configured(
                "HumanClarificationReceived",
                {
                    "request_id": human_feedback.request_id,
                    "answer": human_feedback.answer,
                    "user_id": user_id,
                },
            )
            return {
                "status": "clarification recorded",
            }
        else:
            logging.warning(
                f"No orchestration or plan found for request_id: {human_feedback.request_id}"
            )
            raise HTTPException(
                status_code=404, detail="No active plan found for clarification"
            )


@app_v3.post("/agent_message")
async def agent_message_user(
    agent_message: messages.AgentMessageResponse, request: Request
):
    """
    Endpoint to receive messages from agents (agent -> user communication).

    ---
    tags:
      - Agents
    parameters:
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
    requestBody:
      description: Agent message payload
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              plan_id:
                type: string
                description: ID of the plan this message relates to
              agent:
                type: string
                description: Name or identifier of the agent sending the message
              content:
                type: string
                description: The message content
              agent_type:
                type: string
                description: Type of agent (AI/Human)
              m_plan_id:
                type: string
                description: Optional internal m_plan id
    responses:
      200:
        description: Message recorded successfully
        schema:
          type: object
          properties:
            status:
              type: string
      401:
        description: Missing or invalid user information
    """

    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(
            status_code=401, detail="Missing or invalid user information"
        )
    # Set the approval in the orchestration config

    try:

        result = await PlanService.handle_agent_messages(agent_message, user_id)
        print("Agent message processed:", result)
    except ValueError as ve:
        print(f"ValueError processing agent message: {ve}")
    except Exception as e:
        print(f"Error processing agent message: {e}")

    track_event_if_configured(
        "AgentMessageReceived",
        {
            "agent": agent_message.agent,
            "content": agent_message.content,
            "user_id": user_id,
        },
    )
    return {
        "status": "message recorded",
    }


@app_v3.post("/upload_team_config")
async def upload_team_config(
    request: Request,
    file: UploadFile = File(...),
    team_id: Optional[str] = Query(None),
):
    """
    Upload and save a team configuration JSON file.

    ---
    tags:
      - Team Configuration
    parameters:
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
      - name: file
        in: formData
        type: file
        required: true
        description: JSON file containing team configuration
    responses:
      200:
        description: Team configuration uploaded successfully
      400:
        description: Invalid request or file format
      401:
        description: Missing or invalid user information
      500:
        description: Internal server error
    """
    # Validate user authentication
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(
            status_code=401, detail="Missing or invalid user information"
        )

    # Validate file is provided and is JSON
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    try:
        # Read and parse JSON content
        content = await file.read()
        try:
            json_data = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid JSON format: {str(e)}"
            )

        # Validate content with RAI before processing
        if not team_id:
            rai_valid, rai_error = await rai_validate_team_config(json_data)
            if not rai_valid:
                track_event_if_configured(
                    "Team configuration RAI validation failed",
                    {
                        "status": "failed",
                        "user_id": user_id,
                        "filename": file.filename,
                        "reason": rai_error,
                    },
                )
                raise HTTPException(status_code=400, detail=rai_error)

        track_event_if_configured(
            "Team configuration RAI validation passed",
            {"status": "passed", "user_id": user_id, "filename": file.filename},
        )
        # Initialize memory store and service
        memory_store = await DatabaseFactory.get_database(user_id=user_id)
        team_service = TeamService(memory_store)

        # Validate model deployments
        models_valid, missing_models = await team_service.validate_team_models(
            json_data
        )
        if not models_valid:
            error_message = (
                f"The following required models are not deployed in your Azure AI project: {', '.join(missing_models)}. "
                f"Please deploy these models in Azure AI Foundry before uploading this team configuration."
            )
            track_event_if_configured(
                "Team configuration model validation failed",
                {
                    "status": "failed",
                    "user_id": user_id,
                    "filename": file.filename,
                    "missing_models": missing_models,
                },
            )
            raise HTTPException(status_code=400, detail=error_message)

        track_event_if_configured(
            "Team configuration model validation passed",
            {"status": "passed", "user_id": user_id, "filename": file.filename},
        )

        # Validate search indexes
        search_valid, search_errors = await team_service.validate_team_search_indexes(
            json_data
        )
        if not search_valid:
            error_message = (
                f"Search index validation failed:\n\n{chr(10).join([f'• {error}' for error in search_errors])}\n\n"
                f"Please ensure all referenced search indexes exist in your Azure AI Search service."
            )
            track_event_if_configured(
                "Team configuration search validation failed",
                {
                    "status": "failed",
                    "user_id": user_id,
                    "filename": file.filename,
                    "search_errors": search_errors,
                },
            )
            raise HTTPException(status_code=400, detail=error_message)

        track_event_if_configured(
            "Team configuration search validation passed",
            {"status": "passed", "user_id": user_id, "filename": file.filename},
        )

        # Validate and parse the team configuration
        try:
            team_config = await team_service.validate_and_parse_team_config(
                json_data, user_id
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Save the configuration
        try:
            print("Saving team configuration...", team_id)
            if team_id:
                team_config.team_id = team_id
                team_config.id = team_id  # Ensure id is also set for updates
            team_id = await team_service.save_team_configuration(team_config)
        except ValueError as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to save configuration: {str(e)}"
            )

        track_event_if_configured(
            "Team configuration uploaded",
            {
                "status": "success",
                "team_id": team_id,
                "user_id": user_id,
                "agents_count": len(team_config.agents),
                "tasks_count": len(team_config.starting_tasks),
            },
        )

        return {
            "status": "success",
            "team_id": team_id,
            "name": team_config.name,
            "message": "Team configuration uploaded and saved successfully",
            "team": team_config.model_dump(),  # Return the full team configuration
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error uploading team configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")


@app_v3.get("/team_configs")
async def get_team_configs(request: Request):
    """
    Retrieve all team configurations for the current user.

    ---
    tags:
      - Team Configuration
    parameters:
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
    responses:
      200:
        description: List of team configurations for the user
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              team_id:
                type: string
              name:
                type: string
              status:
                type: string
              created:
                type: string
              created_by:
                type: string
              description:
                type: string
              logo:
                type: string
              plan:
                type: string
              agents:
                type: array
              starting_tasks:
                type: array
      401:
        description: Missing or invalid user information
    """
    # Validate user authentication
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(
            status_code=401, detail="Missing or invalid user information"
        )

    try:
        # Initialize memory store and service
        memory_store = await DatabaseFactory.get_database(user_id=user_id)
        team_service = TeamService(memory_store)

        # Retrieve all team configurations
        team_configs = await team_service.get_all_team_configurations()

        # Convert to dictionaries for response
        configs_dict = [config.model_dump() for config in team_configs]

        return configs_dict

    except Exception as e:
        logging.error(f"Error retrieving team configurations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")


@app_v3.get("/team_configs/{team_id}")
async def get_team_config_by_id(team_id: str, request: Request):
    """
    Retrieve a specific team configuration by ID.

    ---
    tags:
      - Team Configuration
    parameters:
      - name: team_id
        in: path
        type: string
        required: true
        description: The ID of the team configuration to retrieve
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
    responses:
      200:
        description: Team configuration details
        schema:
          type: object
          properties:
            id:
              type: string
            team_id:
              type: string
            name:
              type: string
            status:
              type: string
            created:
              type: string
            created_by:
              type: string
            description:
              type: string
            logo:
              type: string
            plan:
              type: string
            agents:
              type: array
            starting_tasks:
              type: array
      401:
        description: Missing or invalid user information
      404:
        description: Team configuration not found
    """
    # Validate user authentication
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(
            status_code=401, detail="Missing or invalid user information"
        )

    try:
        # Initialize memory store and service
        memory_store = await DatabaseFactory.get_database(user_id=user_id)
        team_service = TeamService(memory_store)

        # Retrieve the specific team configuration
        team_config = await team_service.get_team_configuration(team_id, user_id)

        if team_config is None:
            raise HTTPException(status_code=404, detail="Team configuration not found")

        # Convert to dictionary for response
        return team_config.model_dump()

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logging.error(f"Error retrieving team configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")


@app_v3.delete("/team_configs/{team_id}")
async def delete_team_config(team_id: str, request: Request):
    """
    Delete a team configuration by ID.

    ---
    tags:
      - Team Configuration
    parameters:
      - name: team_id
        in: path
        type: string
        required: true
        description: The ID of the team configuration to delete
      - name: user_principal_id
        in: header
        type: string
        required: true
        description: User ID extracted from the authentication header
    responses:
      200:
        description: Team configuration deleted successfully
        schema:
          type: object
          properties:
            status:
              type: string
            message:
              type: string
            team_id:
              type: string
      401:
        description: Missing or invalid user information
      404:
        description: Team configuration not found
    """
    # Validate user authentication
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(
            status_code=401, detail="Missing or invalid user information"
        )

    try:
        # To do: Check if the team is the users current team, or if it is
        # used in any active sessions/plans.  Refuse request if so.

        # Initialize memory store and service
        memory_store = await DatabaseFactory.get_database(user_id=user_id)
        team_service = TeamService(memory_store)

        # Delete the team configuration
        deleted = await team_service.delete_team_configuration(team_id, user_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Team configuration not found")

        # Track the event
        track_event_if_configured(
            "Team configuration deleted",
            {"status": "success", "team_id": team_id, "user_id": user_id},
        )

        return {
            "status": "success",
            "message": "Team configuration deleted successfully",
            "team_id": team_id,
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logging.error(f"Error deleting team configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")


@app_v3.post("/select_team")
async def select_team(selection: TeamSelectionRequest, request: Request):
    """
    Select the current team for the user session.
    """
    # Validate user authentication
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    if not user_id:
        raise HTTPException(
            status_code=401, detail="Missing or invalid user information"
        )

    if not selection.team_id:
        raise HTTPException(status_code=400, detail="Team ID is required")

    try:
        # Initialize memory store and service
        memory_store = await DatabaseFactory.get_database(user_id=user_id)
        team_service = TeamService(memory_store)

        # Verify the team exists and user has access to it
        team_configuration = await team_service.get_team_configuration(
            selection.team_id, user_id
        )
        if team_configuration is None:  # ensure that id is valid
            raise HTTPException(
                status_code=404,
                detail=f"Team configuration '{selection.team_id}' not found or access denied",
            )
        set_team = await team_service.handle_team_selection(
            user_id=user_id, team_id=selection.team_id
        )
        if not set_team:
            track_event_if_configured(
                "Team selected",
                {
                    "status": "failed",
                    "team_id": selection.team_id,
                    "team_name": team_configuration.name,
                    "user_id": user_id,
                },
            )
            raise HTTPException(
                status_code=404,
                detail=f"Team configuration '{selection.team_id}' failed to set",
            )

        # save to in-memory config for current user
        team_config.set_current_team(
            user_id=user_id, team_configuration=team_configuration
        )

        # Track the team selection event
        track_event_if_configured(
            "Team selected",
            {
                "status": "success",
                "team_id": selection.team_id,
                "team_name": team_configuration.name,
                "user_id": user_id,
            },
        )

        return {
            "status": "success",
            "message": f"Team '{team_configuration.name}' selected successfully",
            "team_id": selection.team_id,
            "team_name": team_configuration.name,
            "agents_count": len(team_configuration.agents),
            "team_description": team_configuration.description,
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logging.error(f"Error selecting team: {str(e)}")
        track_event_if_configured(
            "Team selection error",
            {
                "status": "error",
                "team_id": selection.team_id,
                "user_id": user_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail="Internal server error occurred")


# Get plans is called in the initial side rendering of the frontend
@app_v3.get("/plans")
async def get_plans(request: Request):
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

    # <To do: Francia> Replace the following with code to get plan run history from the database

    # Initialize memory context
    memory_store = await DatabaseFactory.get_database(user_id=user_id)

    current_team = await memory_store.get_current_team(user_id=user_id)
    if not current_team:
        return []

    all_plans = await memory_store.get_all_plans_by_team_id_status(
        user_id=user_id, team_id=current_team.team_id, status=PlanStatus.completed
    )

    return all_plans


# Get plans is called in the initial side rendering of the frontend
@app_v3.get("/plan")
async def get_plan_by_id(
    request: Request,
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

    # <To do: Francia> Replace the following with code to get plan run history from the database

    # Initialize memory context
    memory_store = await DatabaseFactory.get_database(user_id=user_id)
    try:
        if plan_id:
            plan = await memory_store.get_plan_by_plan_id(plan_id=plan_id)
            if not plan:
                track_event_if_configured(
                    "GetPlanBySessionNotFound",
                    {"status_code": 400, "detail": "Plan not found"},
                )
                raise HTTPException(status_code=404, detail="Plan not found")

            # Use get_steps_by_plan to match the original implementation

            team = await memory_store.get_team_by_id(team_id=plan.team_id)
            agent_messages = await memory_store.get_agent_messages(plan_id=plan.plan_id)
            mplan = plan.m_plan if plan.m_plan else None
            streaming_message = plan.streaming_message if plan.streaming_message else ""
            plan.streaming_message = ""  # clear streaming message after retrieval
            plan.m_plan = None  # remove m_plan from plan object for response
            return {
                "plan": plan,
                "team": team if team else None,
                "messages": agent_messages,
                "m_plan": mplan,
                "streaming_message": streaming_message,
            }
        else:
            track_event_if_configured(
                "GetPlanId", {"status_code": 400, "detail": "no plan id"}
            )
            raise HTTPException(status_code=400, detail="no plan id")
    except Exception as e:
        logging.error(f"Error retrieving plan: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")
