# Accelerating your own Multi-Agent -Custom Automation Engine MVP

As the name suggests, this project is designed to accelerate development of Multi-Agent solutions in your environment.  The example solution presented shows how such a solution would be implemented and provides example agent definitions along with stubs for possible tools those agents could use to accomplish tasks.  You will want to implement real functions in your own environment, to be used by agents customized around your own use cases. Users can choose the LLM that is optimized for responsible use. The default LLM is GPT-4o which inherits the existing responsible AI mechanisms and filters from the LLM provider. We encourage developers to review [OpenAI’s Usage policies](https://openai.com/policies/usage-policies/) and [Azure OpenAI’s Code of Conduct](https://learn.microsoft.com/en-us/legal/cognitive-services/openai/code-of-conduct) when using GPT-4o. This document is designed to provide the in-depth technical information to allow you to add these customizations. Once the agents and tools have been developed, you will likely want to implement your own real world front end solution to replace the example in this accelerator.

## Technical Overview

This application is an AI-driven orchestration system that manages a group of AI agents to accomplish tasks based on user input. It uses a FastAPI backend to handle HTTP requests, processes them through various specialized agents, and stores stateful information using Azure Cosmos DB. The system is designed to:

- Receive input tasks from users.
- Generate a detailed plan to accomplish the task using a Planner agent.
- Execute the plan by delegating steps to specialized agents (e.g., HR, Legal, Marketing).
- Incorporate human feedback into the workflow.
- Maintain state across sessions with persistent storage.

This code has not been tested as an end-to-end, reliable production application- it is a foundation to help accelerate building out multi-agent systems. You are encouraged to add your own data and functions to the agents, and then you must apply your own performance and safety evaluation testing frameworks to this system before deploying it.

Below, we'll dive into the details of each component, focusing on the endpoints, data types, and the flow of information through the system.

# Table of Contents

- [Accelerating your own Multi-Agent -Custom Automation Engine MVP](#accelerating-your-own-multi-agent--custom-automation-engine-mvp)
  - [Technical Overview](#technical-overview)
- [Table of Contents](#table-of-contents)
  - [Endpoints](#endpoints)
    - [/input\_task](#input_task)
    - [/human\_feedback](#human_feedback)
    - [/get\_latest\_plan\_by\_session/{session\_id}](#get_latest_plan_by_sessionsession_id)
    - [/get\_steps\_by\_plan/{plan\_id}](#get_steps_by_planplan_id)
    - [/delete\_all\_messages](#delete_all_messages)
  - [Data Types and Models](#data-types-and-models)
    - [Messages](#messages)
      - [InputTask](#inputtask)
      - [Plan](#plan)
      - [Step](#step)
      - [HumanFeedback](#humanfeedback)
      - [ApprovalRequest](#approvalrequest)
      - [ActionRequest](#actionrequest)
      - [ActionResponse](#actionresponse)
    - [Agents](#agents)
      - [Agent Types:](#agent-types)
  - [Application Flow](#application-flow)
    - [Initialization](#initialization)
    - [Input Task Handling](#input-task-handling)
    - [Planning](#planning)
    - [Step Execution and Approval](#step-execution-and-approval)
    - [Human Feedback](#human-feedback)
    - [Action Execution by Specialized Agents](#action-execution-by-specialized-agents)
  - [Agents Overview](#agents-overview)
    - [GroupChatManager](#groupchatmanager)
    - [PlannerAgent](#planneragent)
    - [HumanAgent](#humanagent)
    - [Specialized Agents](#specialized-agents)
  - [Persistent Storage with Cosmos DB](#persistent-storage-with-cosmos-db)
  - [Utilities](#utilities)
    - [`initialize` Function](#initialize-function)
  - [Summary](#summary)

## Endpoints

### /input_task

**Method:** POST  
**Description:** Receives the initial input task from the user.  
**Request Body:** `InputTask`

- `session_id`: Optional string. If not provided, a new UUID will be generated.
- `description`: The description of the task the user wants to accomplish.

**Response:**

- `status`: Confirmation message.
- `session_id`: The session ID associated with the task.
- `plan_id`: The ID of the plan generated.

**Flow:**

1. Generates a `session_id` if not provided.
2. Initializes agents and context for the session.
3. Sends the `InputTask` message to the `GroupChatManager`.
4. Returns the `session_id` and `plan_id`.

### /human_feedback

**Method:** POST  
**Description:** Receives human feedback on a step (e.g., approval, rejection, or modification).  
**Request Body:** `HumanFeedback`

- `step_id`: ID of the step the feedback is related to.
- `plan_id`: ID of the plan.
- `session_id`: The session ID.
- `approved`: Boolean indicating if the step is approved.
- `human_feedback`: Optional string containing any comments.
- `updated_action`: Optional string if the action was modified.

**Response:**

- `status`: Confirmation message.
- `session_id`: The session ID.

**Flow:**

1. Initializes runtime and context for the session.
2. Sends the `HumanFeedback` message to the `HumanAgent`.

### /get_latest_plan_by_session/{session_id}

**Method:** GET  
**Description:** Retrieves the plan associated with a specific session.  
**Response:** List of `Plan` objects.

### /get_steps_by_plan/{plan_id}

**Method:** GET  
**Description:** Retrieves the steps associated with a specific plan.  
**Response:** List of `Step` objects.

### /delete_all_messages

**Method:** DELETE  
**Description:** Deletes all messages across sessions (use with caution).  
**Response:** Confirmation of deletion.

## Data Types and Models

### Messages

#### InputTask

Represents the initial task input from the user.

**Fields:**

- `session_id`: The session ID. Generated if not provided.
- `description`: The description of the task.

#### Plan

Represents a plan containing multiple steps to accomplish the task.

**Fields:**

- `id`: Unique ID of the plan.
- `session_id`: The session ID.
- `initial_goal`: The initial goal derived from the user's input.
- `overall_status`: Status of the plan (in_progress, completed, failed).
- `source`: Origin of the plan (e.g., PlannerAgent).

#### Step

Represents an individual step within a plan.

**Fields:**

- `id`: Unique ID of the step.
- `plan_id`: ID of the plan the step belongs to.
- `action`: The action to be performed.
- `agent`: The agent responsible for the step.
- `status`: Status of the step (e.g., planned, approved, completed).
- `agent_reply`: The response from the agent after executing the action.
- `human_feedback`: Any feedback provided by the human.
- `updated_action`: If the action was modified by human feedback.
- `session_id`: The session ID.

#### HumanFeedback

Contains human feedback on a step, such as approval or rejection.

**Fields:**

- `step_id`: ID of the step the feedback is about.
- `plan_id`: ID of the plan.
- `session_id`: The session ID.
- `approved`: Boolean indicating approval.
- `human_feedback`: Optional comments.
- `updated_action`: Optional modified action.

#### ApprovalRequest

Sent to the HumanAgent to request approval for a step.

**Fields:**

- `step_id`: ID of the step.
- `plan_id`: ID of the plan.
- `session_id`: The session ID.
- `action`: The action to be approved.
- `agent`: The agent responsible for the action.

#### ActionRequest

Sent to specialized agents to perform an action.

**Fields:**

- `step_id`: ID of the step.
- `plan_id`: ID of the plan.
- `session_id`: The session ID.
- `action`: The action to be performed.
- `agent`: The agent that should perform the action.

#### ActionResponse

Contains the response from an agent after performing an action.

**Fields:**

- `step_id`: ID of the step.
- `plan_id`: ID of the plan.
- `session_id`: The session ID.
- `result`: The result of the action.
- `status`: Status of the step (completed, failed).

### Agents

#### Agent Types:

- GroupChatManager
- PlannerAgent
- HumanAgent
- HrAgent
- LegalAgent
- MarketingAgent
- ProcurementAgent
- ProductAgent
- TechSupportAgent

## Application Flow

### Initialization

The initialization process sets up the necessary agents and context for a session. This involves:

- Generating unique AgentIds that include the `session_id` to ensure uniqueness per session.
- Instantiating agents and registering them with the runtime.
- Setting up the Azure OpenAI Chat Completion Client for LLM interactions.
- Creating a `CosmosBufferedChatCompletionContext` for stateful storage.

**Code Reference: `utils.py`**

    async def initialize(session_id: Optional[str] = None) -> Tuple[SingleThreadedAgentRuntime, CosmosBufferedChatCompletionContext]:
        # Generate session_id if not provided
        # Check if session already initialized
        # Initialize agents with unique AgentIds
        # Create Cosmos DB context
        # Register tool agents and specialized agents
        # Start the runtime

### Input Task Handling

When the `/input_task` endpoint receives an `InputTask`, it performs the following steps:

1. Ensures a `session_id` is available.
2. Calls `initialize` to set up agents and context for the session.
3. Creates a `GroupChatManager` agent ID using the `session_id`.
4. Sends the `InputTask` message to the `GroupChatManager`.
5. Returns the `session_id` and `plan_id`.

**Code Reference: `app.py`**

    @app.post("/input_task")
    async def input_task(input_task: InputTask):
        # Initialize session and agents
        # Send InputTask to GroupChatManager
        # Return status, session_id, and plan_id

### Planning

The `GroupChatManager` handles the `InputTask` by:

1. Passing the `InputTask` to the `PlannerAgent`.
2. The `PlannerAgent` generates a `Plan` with detailed `Steps`.
3. The `PlannerAgent` uses LLM capabilities to create a structured plan based on the task description.
4. The plan and steps are stored in the Cosmos DB context.
5. The `GroupChatManager` starts processing the first step.

**Code Reference: `group_chat_manager.py` and `planner.py`**

    # GroupChatManager.handle_input_task
    plan: Plan = await self.send_message(message, self.planner_agent_id)
    await self.memory.add_plan(plan)
    # Start processing steps
    await self.process_next_step(message.session_id)

    # PlannerAgent.handle_input_task
    plan, steps = await self.create_structured_message(...)
    await self.memory.add_plan(plan)
    for step in steps:
        await self.memory.add_step(step)

### Step Execution and Approval

For each step in the plan:

1. The `GroupChatManager` retrieves the next planned step.
2. It sends an `ApprovalRequest` to the `HumanAgent` to get human approval.
3. The `HumanAgent` waits for human feedback (provided via the `/human_feedback` endpoint).
4. The step status is updated to `awaiting_feedback`.

**Code Reference: `group_chat_manager.py`**

    async def process_next_step(self, session_id: str):
        # Get plan and steps
        # Find next planned step
        # Update step status to 'awaiting_feedback'
        # Send ApprovalRequest to HumanAgent

### Human Feedback

The human can provide feedback on a step via the `/human_feedback` endpoint:

1. The `HumanFeedback` message is received by the FastAPI app.
2. The message is sent to the `HumanAgent`.
3. The `HumanAgent` updates the step with the feedback.
4. The `HumanAgent` sends the feedback to the `GroupChatManager`.
5. The `GroupChatManager` either proceeds to execute the step or handles rejections.

**Code Reference: `app.py` and `human.py`**

    # app.py
    @app.post("/human_feedback")
    async def human_feedback(human_feedback: HumanFeedback):
        # Send HumanFeedback to HumanAgent

    # human.py
    @message_handler
    async def handle_human_feedback(self, message: HumanFeedback, ctx: MessageContext):
        # Update step with feedback
        # Send feedback back to GroupChatManager

### Action Execution by Specialized Agents

If a step is approved:

1. The `GroupChatManager` sends an `ActionRequest` to the appropriate specialized agent (e.g., `HrAgent`, `LegalAgent`).
2. The specialized agent executes the action using tools and LLMs.
3. The agent sends an `ActionResponse` back to the `GroupChatManager`.
4. The `GroupChatManager` updates the step status and proceeds to the next step.

**Code Reference: `group_chat_manager.py` and `base_agent.py`**

    # GroupChatManager.execute_step
    action_request = ActionRequest(...)
    await self.send_message(action_request, agent_id)

    # BaseAgent.handle_action_request
    # Execute action using tools and LLM
    # Update step status
    # Send ActionResponse back to GroupChatManager

## Agents Overview

### GroupChatManager

**Role:** Orchestrates the entire workflow.  
**Responsibilities:**

- Receives `InputTask` from the user.
- Interacts with `PlannerAgent` to generate a plan.
- Manages the execution and approval process of each step.
- Handles human feedback and directs approved steps to the appropriate agents.

**Code Reference: `group_chat_manager.py`**

### PlannerAgent

**Role:** Generates a detailed plan based on the input task.  
**Responsibilities:**

- Parses the task description.
- Creates a structured plan with specific actions and agents assigned to each step.
- Stores the plan in the context.
- Handles re-planning if steps fail.

**Code Reference: `planner.py`**

### HumanAgent

**Role:** Interfaces with the human user for approvals and feedback.  
**Responsibilities:**

- Receives `ApprovalRequest` messages.
- Waits for human feedback (provided via the API).
- Updates steps in the context based on feedback.
- Communicates feedback back to the `GroupChatManager`.

**Code Reference: `human.py`**

### Specialized Agents

**Types:** `HrAgent`, `LegalAgent`, `MarketingAgent`, etc.  
**Role:** Execute specific actions related to their domain.  
**Responsibilities:**

- Receive `ActionRequest` messages.
- Perform actions using tools and LLM capabilities.
- Provide results and update steps in the context.
- Communicate `ActionResponse` back to the `GroupChatManager`.

**Common Implementation:**  
All specialized agents inherit from `BaseAgent`, which handles common functionality.  
**Code Reference:** `base_agent.py`, `hr.py`, `legal.py`, etc.

## Persistent Storage with Cosmos DB

The application uses Azure Cosmos DB to store and retrieve session data, plans, steps, and messages. This ensures that the state is maintained across different components and can handle multiple sessions concurrently.

**Key Points:**

- **Session Management:** Stores session information and current status.
- **Plan Storage:** Plans are saved and can be retrieved or updated.
- **Step Tracking:** Each step's status, actions, and feedback are stored.
- **Message History:** Chat messages between agents are stored for context.

**Cosmos DB Client Initialization:**

- Uses `ClientSecretCredential` for authentication.
- Asynchronous operations are used throughout to prevent blocking.

**Code Reference: `cosmos_memory.py`**

## Utilities

### `initialize` Function

**Location:** `utils.py`  
**Purpose:** Initializes agents and context for a session, ensuring that each session has its own unique agents and runtime.  
**Key Actions:**

- Generates unique AgentIds with the `session_id`.
- Creates instances of agents and registers them with the runtime.
- Initializes `CosmosBufferedChatCompletionContext` for session-specific storage.
- Starts the runtime.

**Example Usage:**

    runtime, cosmos_memory = await initialize(input_task.session_id)

## Summary

This application orchestrates a group of AI agents to accomplish user-defined tasks by:

- Accepting tasks via HTTP endpoints.
- Generating detailed plans using LLMs.
- Delegating actions to specialized agents.
- Incorporating human feedback.
- Maintaining state using Azure Cosmos DB.

Understanding the flow of data through the endpoints, agents, and persistent storage is key to grasping the logic of the application. Each component plays a specific role in ensuring tasks are planned, executed, and adjusted based on feedback, providing a robust and interactive system.

For instructions to setup a local development environment for the solution, please see [local deployment guide](./LocalDeployment.md).