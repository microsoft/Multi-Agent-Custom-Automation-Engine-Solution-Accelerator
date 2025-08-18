import uuid
import logging
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request

from auth.auth_utils import get_authenticated_user_details
from common.models.messages_kernel import (
    GeneratePlanRequest,
    InputTask,
    Plan,
    PlanStatus,
)
from common.utils.event_utils import track_event_if_configured
from common.utils.utils_kernel import (
    rai_success,
    rai_validate_team_config,
)
from v3.common.services.team_service import TeamService
from kernel_agents.agent_factory import AgentFactory
from common.database.database_factory import DatabaseFactory
from v3.models.orchestration_models import AgentType
from common.config.app_config import config

app_v3 = APIRouter(
    prefix="/api/v3",
    responses={404: {"description": "Not found"}},
)


@app_v3.post("/create_plan")
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
    if not await rai_success(input_task.description, False):
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
        memory_store = await DatabaseFactory.get_database(user_id=user_id)

        # Create a new Plan object
        plan = Plan(
            session_id=input_task.session_id,
            user_id=user_id,
            initial_goal=input_task.description,
            overall_status=PlanStatus.in_progress,
            source=AgentType.PLANNER.value,
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
        raise HTTPException(status_code=400, detail=f"Error creating plan: {e}") from e


@app_v3.post("/generate_plan")
async def generate_plan_endpoint(
    generate_plan_request: GeneratePlanRequest, request: Request
):
    """
    Generate plan steps for an existing plan using the planner agent.

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
            plan_id:
              type: string
              description: The ID of the existing plan to generate steps for
    responses:
      200:
        description: Plan generation completed successfully
        schema:
          type: object
          properties:
            status:
              type: string
              description: Success message
            plan_id:
              type: string
              description: The ID of the plan that was generated
            steps_created:
              type: integer
              description: Number of steps created
      400:
        description: Invalid request or processing error
        schema:
          type: object
          properties:
            detail:
              type: string
              description: Error message
      404:
        description: Plan not found
        schema:
          type: object
          properties:
            detail:
              type: string
              description: Error message
    """
    # Get authenticated user
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    if not user_id:
        track_event_if_configured(
            "UserIdNotFound", {"status_code": 400, "detail": "no user"}
        )
        raise HTTPException(status_code=400, detail="no user")

    try:
        # Initialize memory store
        memory_store = await DatabaseFactory.get_database(user_id=user_id)

        # Get the existing plan
        plan = await memory_store.get_plan_by_plan_id(
            plan_id=generate_plan_request.plan_id
        )
        if not plan:
            track_event_if_configured(
                "GeneratePlanNotFound",
                {
                    "status_code": 404,
                    "detail": "Plan not found",
                    "plan_id": generate_plan_request.plan_id,
                },
            )
            raise HTTPException(status_code=404, detail="Plan not found")

        # Create the agents for this session
        client = None
        try:
            client = config.get_ai_project_client()
        except Exception as client_exc:
            logging.error(f"Error creating AIProjectClient: {client_exc}")

        agents = await AgentFactory.create_all_agents(
            session_id=plan.session_id,
            user_id=user_id,
            memory_store=memory_store,
            client=client,
        )

        # Get the group chat manager to process the plan
        group_chat_manager = agents[AgentType.GROUP_CHAT_MANAGER.value]

        # Create an InputTask from the plan's initial goal
        input_task = InputTask(
            session_id=plan.session_id, description=plan.initial_goal
        )

        # Use the group chat manager to generate the plan steps
        await group_chat_manager.handle_input_task(input_task)

        # Get the updated plan with steps
        updated_plan = await memory_store.get_plan_by_plan_id(
            plan_id=generate_plan_request.plan_id
        )
        steps = await memory_store.get_steps_by_plan(
            plan_id=generate_plan_request.plan_id
        )

        # Log successful plan generation
        track_event_if_configured(
            "PlanGenerated",
            {
                "status": f"Plan generation completed for plan ID: {generate_plan_request.plan_id}",
                "plan_id": generate_plan_request.plan_id,
                "session_id": plan.session_id,
                "steps_created": len(steps),
            },
        )

        if client:
            try:
                client.close()
            except Exception as e:
                logging.error(f"Error closing AIProjectClient: {e}")

        return {
            "status": "Plan generation completed successfully",
            "plan_id": generate_plan_request.plan_id,
            "steps_created": len(steps),
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        track_event_if_configured(
            "GeneratePlanError",
            {
                "plan_id": generate_plan_request.plan_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=400, detail=f"Error generating plan: {e}")


@app_v3.post("/upload_team_config")
async def upload_team_config_endpoint(request: Request, file: UploadFile = File(...)):
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
                "team_id": team_config.team_id,
                "user_id": user_id,
                "agents_count": len(team_config.agents),
                "tasks_count": len(team_config.starting_tasks),
            },
        )

        return {
            "status": "success",
            "team_id": team_id,
            "team_id": team_config.team_id,
            "name": team_config.name,
            "message": "Team configuration uploaded and saved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error uploading team configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")


@app_v3.get("/team_configs")
async def get_team_configs_endpoint(request: Request):
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
        team_configs = await team_service.get_all_team_configurations(user_id)

        # Convert to dictionaries for response
        configs_dict = [config.model_dump() for config in team_configs]

        return configs_dict

    except Exception as e:
        logging.error(f"Error retrieving team configurations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")


@app_v3.get("/team_configs/{team_id}")
async def get_team_config_by_id_endpoint(team_id: str, request: Request):
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
async def delete_team_config_endpoint(team_id: str, request: Request):
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


@app_v3.get("/model_deployments")
async def get_model_deployments_endpoint(request: Request):
    """
    Get information about available model deployments for debugging/validation.

    ---
    tags:
      - Model Validation
    responses:
      200:
        description: List of available model deployments
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
        team_service = TeamService()
        deployments = await team_service.list_model_deployments()
        summary = await team_service.get_deployment_status_summary()
        return {"deployments": deployments, "summary": summary}
    except Exception as e:
        logging.error(f"Error retrieving model deployments: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")


@app_v3.get("/search_indexes")
async def get_search_indexes_endpoint(request: Request):
    """
    Get information about available search indexes for debugging/validation.

    ---
    tags:
      - Search Validation
    responses:
      200:
        description: List of available search indexes
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
        team_service = TeamService()
        summary = await team_service.get_search_index_summary()
        return {"search_summary": summary}
    except Exception as e:
        logging.error(f"Error retrieving search indexes: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")
