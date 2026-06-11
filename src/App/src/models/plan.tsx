import { AgentMessageData } from './agentMessage';
import { PlanStatus, AgentMessageType } from './enums';
import { StreamingPlanUpdate } from './messages';
import { TeamConfig } from './Team';

/**
 * Base interface with common fields
 */
export interface BaseModel {
    /** Unique identifier */
    id: string;
    /** Timestamp when created */
    session_id: string;
    /** Timestamp when last updated */
    timestamp: string;
}

// these entries as they are comming from db
export interface TeamAgentBE {
    /** Input key for the agent */
    input_key: string;
    /** Type of the agent */
    type: string;
    /** Name of the agent */
    name: string;
    /** Deployment name for the agent */
    deployment_name: string;
    /** System message for the agent */
    system_message?: string;
    /** Description of the agent */
    description?: string;
    /** Icon for the agent */
    icon?: string;
    /** Index name for RAG capabilities */
    index_name?: string;
    /** Whether the agent uses RAG */
    use_rag?: boolean;
    /** Whether the agent uses MCP (Model Context Protocol) */
    use_mcp?: boolean;
    /** Whether the agent uses Bing search */
    use_bing?: boolean;
    /** Whether the agent uses reasoning */
    use_reasoning?: boolean;
    /** Whether the agent has coding tools */
    coding_tools?: boolean;
}

/**
 * Represents a starting task for a team.
 */
export interface StartingTaskBE {
    /** Unique identifier for the task */
    id: string;
    /** Name of the task */
    name: string;
    /** Prompt for the task */
    prompt: string;
    /** Creation timestamp */
    created: string;
    /** Creator of the task */
    creator: string;
    /** Logo for the task */
    logo: string;
}

/**
 * Represents a team configuration stored in the database.
 */
export interface TeamConfigurationBE extends BaseModel {
    /** The type of data model */
    data_type: "team_config";
    /** Team identifier */
    team_id: string;
    /** Name of the team */
    name: string;
    /** Status of the team */
    status: string;
    /** Creation timestamp */
    created: string;
    /** Creator of the team */
    created_by: string;
    /** List of agents in the team */
    agents: TeamAgentBE[];
    /** Description of the team */
    description?: string;
    /** Logo for the team */
    logo?: string;
    /** Plan for the team */
    plan?: string;
    /** Starting tasks for the team */
    starting_tasks: StartingTaskBE[];
    /** User who uploaded this configuration */
    user_id: string;
}

/**
 * Represents a plan containing multiple steps.
 */
export interface Plan extends BaseModel {
    /** The type of data model */
    data_type: "plan";
    /** Plan identifier */
    plan_id: string;
    /** User identifier */
    user_id: string;
    /** Initial goal/title of the plan */
    initial_goal: string;
    /** Current status of the plan */
    overall_status: PlanStatus;
    /** Whether the plan is approved */
    approved?: boolean;
    /** Source of the plan (typically the planner agent) */
    source?: string;
    /** Summary of the plan */
    summary?: string;
    /** Team identifier associated with the plan */
    team_id?: string;
    /** Human clarification request text */
    human_clarification_request?: string;
    /** Human clarification response text */
    human_clarification_response?: string;
}

export interface MStepBE {
    /** Agent responsible for the step */
    agent: string;
    /** Action to be performed */
    action: string;
}
/**
 * Represents a user request item within the user_request object
 */
export interface UserRequestItem {
    /** AI model identifier */
    ai_model_id?: string | null;
    /** Metadata */
    metadata?: Record<string, any>;
    /** Content type */
    content_type?: string;
    /** Text content */
    text?: string;
    /** Encoding */
    encoding?: string | null;
}

/**
 * Represents the user_request object structure from the database
 */
export interface UserRequestObject {
    /** AI model identifier */
    ai_model_id?: string | null;
    /** Metadata */
    metadata?: Record<string, any>;
    /** Content type */
    content_type?: string;
    /** Role */
    role?: string;
    /** Name */
    name?: string | null;
    /** Items array containing the actual request text */
    items?: UserRequestItem[];
    /** Encoding */
    encoding?: string | null;
    /** Finish reason */
    finish_reason?: string | null;
    /** Status */
    status?: string | null;
}

export interface MPlanBE {

    /** Unique identifier */
    id: string;
    /** User identifier */
    user_id: string;
    /** Team identifier */
    team_id: string;
    /** Associated plan identifier */
    plan_id: string;
    /** Overall status of the plan */
    overall_status: PlanStatus;
    /** User's original request - can be string or complex object */
    user_request: string | UserRequestObject;
    /** List of team member names */
    team: string[];
    /** Facts or context for the plan */
    facts: string;
    /** List of steps in the plan */
    steps: MStepBE[];
}
export interface AgentMessageBE extends BaseModel {
    /** The type of data model */
    data_type: "m_plan_message";
    /** Plan identifier */
    plan_id: string;
    /** User identifier */
    user_id: string;
    /** Agent name or identifier */
    agent: string;
    /** Associated m_plan identifier */
    m_plan_id?: string;
    /** Type of agent (Human or AI) */
    agent_type: AgentMessageType;
    /** Message content */
    content: string;
    /** Raw data associated with the message */
    raw_data: string;
    /** Steps associated with the message */
    steps: any[];
    /** Next steps associated with the message */
    next_steps: any[];
}

export interface PlanFromAPI {
    plan: Plan;
    messages: AgentMessageBE[];
    m_plan: MPlanBE | null;
    team: TeamConfigurationBE | null;
    streaming_message: string | null;
}
/**
 * Interface for processed plan data
 */
export interface ProcessedPlanData {
    plan: Plan;
    team: TeamConfig | null;
    messages: AgentMessageData[];
    mplan: MPlanData | null;
    streaming_message: string | null;
}


export interface PlanChatProps {
    planData: ProcessedPlanData;
    input: string;
    loading: boolean;
    setInput: any;
    submittingChatDisableInput: boolean;
    OnChatSubmit: (message: string) => void;
    streamingMessages?: StreamingPlanUpdate[];
    wsConnected?: boolean;
    onPlanApproval?: (approved: boolean) => void;
}

export interface MPlanData {
    id: string;
    status: string;
    user_request: string;
    team: string[];
    facts: string;
    steps: Array<{
        id: number;
        action: string;
        cleanAction: string;
        agent?: string;
    }>;
    context: {
        task: string;
        participant_descriptions: Record<string, string>;
    };
    // Additional fields from m_plan
    user_id?: string;
    team_id?: string;
    plan_id?: string;
    overall_status?: string;
    raw_data?: any;
}

export interface PlanApprovalRequest {
    m_plan_id: string;
    plan_id: string;
    approved: boolean;
    feedback?: string;
}

export interface PlanApprovalResponse {
    status: string;
    message?: string;
}
