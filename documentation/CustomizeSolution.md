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

- [Accelerating your own Multi-Agent - Custom Automation Engine MVP](#accelerating-your-own-multi-agent---custom-automation-engine-mvp)
  - [Technical Overview](#technical-overview)
- [Table of Contents](#table-of-contents)
  - [Endpoints](#endpoints)
    - [/input\_task](#input_task)
    - [/human\_feedback](#human_feedback)
    - [/get\_latest\_plan\_by\_session/{session\_id}](#get_latest_plan_by_session-session_id)
    - [/steps/{plan\_id}](#stepsplan_id)
    - [/agent\_messages/{session\_id}](#agent_messagessession_id)
    - [/messages](#messages)
    - [/delete\_all\_messages](#delete_all_messages)
    - [/api/agent-tools](#apiagent-tools)
  - [Data Types and Models](#data-types-and-models)
    - [Messages](#messages)
      - [BaseDataModel](#basedatamodel)
      - [AgentMessage](#agentmessage)
      - [Session](#session)
      - [Plan](#plan)
      - [Step](#step)
      - [PlanWithSteps](#planwithsteps)
      - [InputTask](#inputtask)
      - [ApprovalRequest](#approvalrequest)
      - [HumanFeedback](#humanfeedback)
      - [HumanClarification](#humanclarification)
      - [ActionRequest](#actionrequest)
      - [ActionResponse](#actionresponse)
      - [PlanStateUpdate](#planstateupdate)
      - [GroupChatMessage](#groupchatmessage)
      - [RequestToSpeak](#requesttospeak)
    - [Enums](#enums)
      - [DataType](#datatype)
      - [BAgentType](#bagenttype)
      - [StepStatus](#stepstatus)
      - [PlanStatus](#planstatus)
      - [HumanFeedbackStatus](#humanfeedbackstatus)
  - [Application Flow](#application-flow)
    - [Initialization](#initialization)
  - [Agents Overview](#agents-overview)
    - [GroupChatManager](#groupchatmanager)
    - [PlannerAgent](#planneragent)
    - [HumanAgent](#humanagent)
    - [Specialized Agents](#specialized-agents)
  - [Persistent Storage with Cosmos DB](#persistent-storage-with-cosmos-db)
  - [Utilities](#utilities)
    - [`initialize_runtime_and_context` Function](#initialize_runtime_and_context-function)
  - [Summary](#summary)


## Endpoints

### /input_task

**Method:** POST  
**Description:** Receives the initial input task from the user.  

**Request Headers:**

- `user_principal_id`: User ID (`user_id`) extracted from the authentication header.

**Request Body:** `InputTask`
- `session_id`: Optional string. If not provided, a new UUID will be generated.
- `description`: The description of the task the user wants to accomplish.


**Response:**
- `status`: Confirmation message.
- `session_id`: The session ID associated with the task.
- `plan_id`: The ID of the plan generated.
- `description`: The task description.


**Flow:**
1. Validates header and extracts `user_principal_id` as  `user_id`.
2. Generates a `session_id` if not provided.
3. Initializes agents and context for the session.
4. Sends the `InputTask` message to the `GroupChatManager`.
5. Returns the `status`, `session_id`, `plan_id`, `description`, and `user_id`.


### /human_feedback

**Method:** POST  
**Description:** Receives human feedback on a step (e.g., approval, rejection, or modification).  

**Request Headers:**
- `user_principal_id`: User ID (`user_id`) extracted from the authentication header.

**Request Body:** `HumanFeedback`
- `step_id`: The ID of the step to provide feedback for.
- `plan_id`: The ID of the plan.
- `session_id`: The session ID.
- `approved`: Boolean indicating if the step is approved.
- `human_feedback`: Optional string containing any comments.
- `updated_action`: Optional string if the action was modified.

**Response:**
- `status`: Confirmation message.
- `session_id`: The session ID.
- `step_id`: The step ID associated with the feedback.

**Flow:**
1. Validates header and extracts `user_principal_id` as  `user_id`.
2. Initializes runtime and context for the session.
3. Sends the `HumanFeedback` message to the `HumanAgent`.
4. Returns the `status`, `session_id`, and `step_id`.


### /human_clarification_on_plan

**Method:** POST  
**Description:** Receives human clarification on a plan.  

**Request Headers:**
- `user_principal_id`: User ID (`user_id`) extracted from the authentication header.

**Request Body:** `HumanClarification`
- `plan_id`: The ID of the plan requiring clarification.
- `session_id`: The session ID associated with the plan.
- `human_clarification`: Clarification details provided by the user.

**Response:**
- `status`: Confirmation message.
- `session_id`: The session ID associated with the plan.

**Flow:**
1. Validates header and extracts `user_principal_id` as  `user_id`.
2. Initializes runtime and context for the session.
3. Sends the `HumanClarification` message to the `PlannerAgent`.
4. Returns the `status` and `session_id`.

### /approve_step_or_steps

**Method:** POST  
**Description:** Approves a step or multiple steps in a plan.  

**Request Headers:**

- `user_principal_id`: User ID (`user_id`) extracted from the authentication header.

**Request Body:** `HumanFeedback`
- `step_id`: Optional step ID to approve. If not provided, all steps are approved.
- `plan_id`: The ID of the plan.
- `session_id`: The session ID associated with the plan.
- `approved`: Boolean indicating whether the step(s) are approved.
- `human_feedback`: Optional string containing any comments.
- `updated_action`: Optional string if the action was modified.

**Response:**
- `status`: A confirmation message indicating the approval result.

**Flow:**
1. Validates header and extracts `user_principal_id` as  `user_id`.
2. Initializes runtime and context for the session.
3. Sends the `HumanFeedback` approval message to the `GroupChatManager`.
4. If `step_id` is provided, approves the specific step; otherwise, approves all steps.
5. Returns the `status` message indicating the result of the approval.

### /plans

**Method:** GET  
**Description:** Retrieves all plans for the current user or the plan for a specific session.  

**Request Headers:**

- `user_principal_id`: User ID (`user_id`) extracted from the authentication header.

**Query Parameters:**
- `session_id` (optional): Retrieve the plan for this specific session ID. If not provided, all plans for the user are retrieved.

**Response:**
- A list of plans with their details:
  - `id`: Unique ID of the plan.
  - `session_id`: The session ID associated with the plan.
  - `initial_goal`: The initial goal derived from the user's input.
  - `overall_status`: The status of the plan (e.g., in_progress, completed, failed).
  - `steps`: A list of steps associated with the plan, each including:
    - `id`: Unique ID of the step.
    - `plan_id`: ID of the plan the step belongs to.
    - `action`: The action to be performed.
    - `agent`: The agent responsible for the step.
    - `status`: The status of the step (e.g., planned, approved, completed).
    - `agent_reply`: Optional response from the agent after execution.
    - `human_feedback`: Optional feedback provided by the user.
    - `updated_action`: Optional modified action based on feedback.

**Flow:**
1. Validates header and extracts `user_principal_id` as  `user_id`.
2. If `session_id` is provided:
   - Retrieves the plan for the specified session ID.
   - Fetches the steps for the plan.
3. If `session_id` is not provided:
   - Retrieves all plans for the user.
   - Fetches the steps for each plan concurrently.
4. Returns the plan(s) along with their steps.

### /steps/{plan_id}

**Method:** GET  
**Description:** Retrieves all steps associated with a specific plan.  

**Request Headers:**

- `user_principal_id`: User ID (`user_id`) extracted from the authentication header.

**Path Parameters:**
- `plan_id`: The ID of the plan to retrieve steps for.

**Response:**
- A list of steps with their details:
  - `id`: Unique ID of the step.
  - `plan_id`: The ID of the plan the step belongs to.
  - `action`: The action to be performed.
  - `agent`: The agent responsible for the step.
  - `status`: The status of the step (e.g., planned, approved, completed).
  - `agent_reply`: Optional response from the agent after execution.
  - `human_feedback`: Optional feedback provided by the user.
  - `updated_action`: Optional modified action based on feedback.

**Flow:**
1. Validates header and extracts `user_principal_id` as  `user_id`.
2. Retrieves the steps for the specified `plan_id`.
3. Returns the list of steps with their details.

### /agent_messages/{session_id}

**Method:** GET  
**Description:** Retrieves all agent messages for a specific session.  

**Request Headers:**
- `user_principal_id`: User ID (`user_id`) extracted from the authentication header.

**Path Parameters:**
- `session_id`: The ID of the session to retrieve agent messages for.

**Response:**
- A list of agent messages with their details:
  - `id`: Unique ID of the agent message.
  - `session_id`: The session ID associated with the message.
  - `plan_id`: The ID of the plan related to the agent message.
  - `content`: The content of the message.
  - `source`: The source of the message (e.g., agent type).
  - `ts`: The timestamp of the message.
  - `step_id`: Optional step ID associated with the message.

**Flow:**
1. Validates header and extracts `user_principal_id` as  `user_id`.
2. Retrieves the agent messages for the specified `session_id`.
3. Returns the list of agent messages with their details.

### /messages

**Method:** DELETE  
**Description:** Deletes all messages across sessions.  

**Request Headers:**

- `user_principal_id`: User ID (`user_id`) extracted from the authentication header.

**Response:**
- A confirmation message:
  - `status`: A status message indicating all messages were deleted.

**Flow:**
1. Validates header and extracts `user_principal_id` as  `user_id`.
2. Deletes all messages across sessions, including:
   - Plans
   - Sessions
   - Steps
   - Agent messages
3. Returns a confirmation `status` message.

### /messages

**Method:** GET  
**Description:** Retrieves all messages across sessions.  

**Request Headers:**

- `user_principal_id`: User ID (`user_id`) extracted from the authentication header.

**Response:**
- A list of all messages with their details:
  - `id`: Unique ID of the message.
  - `data_type`: The type of the message (e.g., session, step, plan, agent_message).
  - `session_id`: The session ID associated with the message.
  - `content`: The content of the message.
  - `ts`: The timestamp of the message.

**Flow:**
1. Validates header and extracts `user_principal_id` as  `user_id`.
2. Retrieves all messages across sessions.
3. Returns the list of messages with their details.

### /api/agent-tools

**Method:** GET  
**Description:** Retrieves all available agent tools and their descriptions.  

**Response:**
- A list of agent tools with their details:
  - `agent`: The name of the agent associated with the tool.
  - `function`: The name of the tool function.
  - `description`: A detailed description of what the tool does.
  - `arguments`: The arguments required by the tool function.

**Flow:**
1. Retrieves all agent tools and their metadata.
2. Returns the list of agent tools with their details.


## Models and Datatypes
### Models
#### **`BaseDataModel`**
The `BaseDataModel` is a foundational class for creating structured data models using Pydantic. It provides the following attributes:

- **`id`**: A unique identifier for the data, generated using `uuid`.
- **`ts`**: An optional timestamp indicating when the model instance was created or modified.

#### **`AgentMessage`**
The `AgentMessage` model represents communication between agents and includes the following fields:

- **`id`**: A unique identifier for the message, generated using `uuid`.
- **`data_type`**: A literal value of `"agent_message"` to identify the message type.
- **`session_id`**: The session associated with this message.
- **`user_id`**: The ID of the user associated with this message.
- **`plan_id`**: The ID of the related plan.
- **`content`**: The content of the message.
- **`source`**: The origin or sender of the message (e.g., an agent).
- **`ts`**: An optional timestamp for when the message was created.
- **`step_id`**: An optional ID of the step associated with this message.

#### **`Session`**
The `Session` model represents a user session and extends the `BaseDataModel`. It has the following attributes:

- **`data_type`**: A literal value of `"session"` to identify the type of data.
- **`current_status`**: The current status of the session (e.g., `active`, `completed`).
- **`message_to_user`**: An optional field to store any messages sent to the user.
- **`ts`**: An optional timestamp for the session's creation or last update.


#### **`Plan`**
The `Plan` model represents a high-level structure for organizing actions or tasks. It extends the `BaseDataModel` and includes the following attributes:

- **`data_type`**: A literal value of `"plan"` to identify the data type.
- **`session_id`**: The ID of the session associated with this plan.
- **`initial_goal`**: A description of the initial goal derived from the user’s input.
- **`overall_status`**: The overall status of the plan (e.g., `in_progress`, `completed`, `failed`).

#### **`Step`**
The `Step` model represents a discrete action or task within a plan. It extends the `BaseDataModel` and includes the following attributes:

- **`data_type`**: A literal value of `"step"` to identify the data type.
- **`plan_id`**: The ID of the plan the step belongs to.
- **`action`**: The specific action or task to be performed.
- **`agent`**: The name of the agent responsible for executing the step.
- **`status`**: The status of the step (e.g., `planned`, `approved`, `completed`).
- **`agent_reply`**: An optional response from the agent after executing the step.
- **`human_feedback`**: Optional feedback provided by a user about the step.
- **`updated_action`**: Optional modified action based on human feedback.
- **`session_id`**: The session ID associated with the step.
- **`user_id`**: The ID of the user providing feedback or interacting with the step.

#### **`PlanWithSteps`**
The `PlanWithSteps` model extends the `Plan` model and includes additional information about the steps in the plan. It has the following attributes:

- **`steps`**: A list of `Step` objects associated with the plan.
- **`total_steps`**: The total number of steps in the plan.
- **`completed_steps`**: The number of steps that have been completed.
- **`pending_steps`**: The number of steps that are pending approval or completion.

**Additional Features**:
The `PlanWithSteps` model provides methods to update step counts:
- `update_step_counts()`: Calculates and updates the `total_steps`, `completed_steps`, and `pending_steps` fields based on the associated steps.

#### **`InputTask`**
The `InputTask` model represents the user’s initial input for creating a plan. It includes the following attributes:

- **`session_id`**: An optional string for the session ID. If not provided, a new UUID will be generated.
- **`description`**: A string describing the task or goal the user wants to accomplish.
- **`user_id`**: The ID of the user providing the input.

#### **`ApprovalRequest`**
The `ApprovalRequest` model represents a request to approve a step or multiple steps. It includes the following attributes:

- **`step_id`**: An optional string representing the specific step to approve. If not provided, the request applies to all steps.
- **`plan_id`**: The ID of the plan containing the step(s) to approve.
- **`session_id`**: The ID of the session associated with the approval request.
- **`approved`**: A boolean indicating whether the step(s) are approved.
- **`human_feedback`**: An optional string containing comments or feedback from the user.
- **`updated_action`**: An optional string representing a modified action based on feedback.
- **`user_id`**: The ID of the user making the approval request.


#### **`HumanFeedback`**
The `HumanFeedback` model captures user feedback on a specific step or plan. It includes the following attributes:

- **`step_id`**: The ID of the step the feedback is related to.
- **`plan_id`**: The ID of the plan containing the step.
- **`session_id`**: The session ID associated with the feedback.
- **`approved`**: A boolean indicating if the step is approved.
- **`human_feedback`**: Optional comments or feedback provided by the user.
- **`updated_action`**: Optional modified action based on the feedback.
- **`user_id`**: The ID of the user providing the feedback.

#### **`HumanClarification`**
The `HumanClarification` model represents clarifications provided by the user about a plan. It includes the following attributes:

- **`plan_id`**: The ID of the plan requiring clarification.
- **`session_id`**: The session ID associated with the plan.
- **`human_clarification`**: The clarification details provided by the user.
- **`user_id`**: The ID of the user providing the clarification.

#### **`ActionRequest`**
The `ActionRequest` model captures a request to perform an action within the system. It includes the following attributes:

- **`session_id`**: The session ID associated with the action request.
- **`plan_id`**: The ID of the plan associated with the action.
- **`step_id`**: Optional ID of the step associated with the action.
- **`action`**: A string describing the action to be performed.
- **`user_id`**: The ID of the user requesting the action.

#### **`ActionResponse`**
The `ActionResponse` model represents the response to an action request. It includes the following attributes:

- **`status`**: A string indicating the status of the action (e.g., `success`, `failure`).
- **`message`**: An optional string providing additional details or context about the action's result.
- **`data`**: Optional data payload containing any relevant information from the action.
- **`user_id`**: The ID of the user associated with the action response.

#### **`PlanStateUpdate`**
The `PlanStateUpdate` model represents an update to the state of a plan. It includes the following attributes:

- **`plan_id`**: The ID of the plan being updated.
- **`session_id`**: The session ID associated with the plan.
- **`new_state`**: A string representing the new state of the plan (e.g., `in_progress`, `completed`, `failed`).
- **`user_id`**: The ID of the user making the state update.
- **`timestamp`**: An optional timestamp indicating when the update was made.

---

#### **`GroupChatMessage`**
The `GroupChatMessage` model represents a message sent in a group chat context. It includes the following attributes:

- **`message_id`**: A unique ID for the message.
- **`session_id`**: The session ID associated with the group chat.
- **`user_id`**: The ID of the user sending the message.
- **`content`**: The text content of the message.
- **`timestamp`**: A timestamp indicating when the message was sent.

---

#### **`RequestToSpeak`**
The `RequestToSpeak` model represents a user's request to speak or take action in a group chat or collaboration session. It includes the following attributes:

- **`request_id`**: A unique ID for the request.
- **`session_id`**: The session ID associated with the request.
- **`user_id`**: The ID of the user making the request.
- **`reason`**: A string describing the reason or purpose of the request.
- **`timestamp`**: A timestamp indicating when the request was made.


### Data Types

#### **`DataType`**
The `DataType` enumeration defines the types of data used in the system. Possible values include:
- **`plan`**: Represents a plan data type.
- **`session`**: Represents a session data type.
- **`step`**: Represents a step data type.
- **`agent_message`**: Represents an agent message data type.

---

#### **`BAgentType`**
The `BAgentType` enumeration defines the types of agents in the system. Possible values include:
- **`human`**: Represents a human agent.
- **`ai_assistant`**: Represents an AI assistant agent.
- **`external_service`**: Represents an external service agent.

#### **`StepStatus`**
The `StepStatus` enumeration defines the possible statuses for a step. Possible values include:
- **`planned`**: Indicates the step is planned but not yet approved or completed.
- **`approved`**: Indicates the step has been approved.
- **`completed`**: Indicates the step has been completed.
- **`failed`**: Indicates the step has failed.


#### **`PlanStatus`**
The `PlanStatus` enumeration defines the possible statuses for a plan. Possible values include:
- **`in_progress`**: Indicates the plan is currently in progress.
- **`completed`**: Indicates the plan has been successfully completed.
- **`failed`**: Indicates the plan has failed.


#### **`HumanFeedbackStatus`**
The `HumanFeedbackStatus` enumeration defines the possible statuses for human feedback. Possible values include:
- **`pending`**: Indicates the feedback is awaiting review or action.
- **`addressed`**: Indicates the feedback has been addressed.
- **`rejected`**: Indicates the feedback has been rejected.


### Application Flow

#### **Initialization**

The initialization process sets up the necessary agents and context for a session. This involves:

- **Generating Unique AgentIds**: Each agent is assigned a unique `AgentId` based on the `session_id`, ensuring that multiple sessions can operate independently.
- **Instantiating Agents**: Various agents, such as `PlannerAgent`, `HrAgent`, and `GroupChatManager`, are initialized and registered with unique `AgentIds`.
- **Setting Up Azure OpenAI Client**: The Azure OpenAI Chat Completion Client is initialized to handle LLM interactions with support for function calling, JSON output, and vision handling.
- **Creating Cosmos DB Context**: A `CosmosBufferedChatCompletionContext` is established for stateful interaction storage.

**Code Reference: `utils.py`**

**Steps:**
1. **Session ID Generation**: If `session_id` is not provided, a new UUID is generated.
2. **Agent Registration**: Each agent is assigned a unique `AgentId` and registered with the runtime.
3. **Azure OpenAI Initialization**: The LLM client is configured for advanced interactions.
4. **Cosmos DB Context Creation**: A buffered context is created for storing stateful interactions.
5. **Runtime Start**: The runtime is started, enabling communication and agent operation.



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