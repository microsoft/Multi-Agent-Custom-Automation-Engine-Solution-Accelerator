import { AgentType, PlanStatus, StepStatus, HumanFeedbackStatus } from './enums';

/**
 * Base interface with common fields
 */
export interface BaseModel {
    /** Unique identifier for the model */
    id: string;
    /** Timestamp when the model was created or updated */
    timestamp: string;
}

/**
 * Represents a plan containing multiple steps.
 */
export interface Plan extends BaseModel {
    /** The type of data model */
    data_type: "plan";
    /** Session identifier */
    session_id: string;
    /** User identifier */
    user_id: string;
    /** The initial goal or task description */
    initial_goal: string;
    /** Current status of the plan */
    overall_status: PlanStatus;
    /** Source of the plan */
    source: string;
    /** Optional summary of the plan */
    summary?: string;
    /** Optional clarification request */
    human_clarification_request?: string;
    /** Optional response to clarification request */
    human_clarification_response?: string;
}

/**
 * Represents an individual step (task) within a plan.
 */
export interface Step extends BaseModel {
    /** The type of data model */
    data_type: "step";
    /** Plan identifier */
    plan_id: string;
    /** Session identifier (Partition key) */
    session_id: string;
    /** User identifier */
    user_id: string;
    /** Action to be performed */
    action: string;
    /** Agent assigned to this step */
    agent: AgentType;
    /** Current status of the step */
    status: StepStatus;
    /** Optional reply from the agent */
    agent_reply?: string;
    /** Optional feedback from human */
    human_feedback?: string;
    /** Optional human approval status */
    human_approval_status?: HumanFeedbackStatus;
    /** Optional updated action */
    updated_action?: string;
}
export interface PlanMessage extends BaseModel {
    /** The type of data model */
    data_type: "agent_message";
    /** Session identifier */
    session_id: string;
    /** User identifier */
    user_id: string;
    /** Plan identifier */
    plan_id: string;
    /** Message content */
    content: string;
    /** Source of the message */
    source: string;
    /** Step identifier */
    step_id: string;
}
/**
 * Represents a plan that includes its associated steps.
 */
export interface PlanWithSteps extends Plan {
    /** Steps associated with this plan */
    steps: Step[];
    /** Total number of steps */
    total_steps: number;
    /** Count of steps in planned status */
    planned: number;
    /** Count of steps awaiting feedback */
    awaiting_feedback: number;
    /** Count of steps approved */
    approved: number;
    /** Count of steps rejected */
    rejected: number;
    /** Count of steps with action requested */
    action_requested: number;
    /** Count of steps completed */
    completed: number;
    /** Count of steps failed */
    failed: number;
}


/**
 * Interface for processed plan data
 */
export interface ProcessedPlanData {
    plan: PlanWithSteps;
    agents: AgentType[];
    steps: Step[];
    hasClarificationRequest: boolean;
    hasClarificationResponse: boolean;
    enableChat: boolean;
    enableStepButtons: boolean;
    messages: PlanMessage[];
}

export interface PlanChatProps {
    planData: ProcessedPlanData;
    input: string;
    loading: boolean;
    setInput: any;
    submittingChatDisableInput: boolean;
    OnChatSubmit: (message: string) => void;
}