import { AgentType, StepStatus, PlanStatus } from './enums';

/**
 * Message roles compatible with Semantic Kernel
 */
export enum MessageRole {
    SYSTEM = "system",
    USER = "user",
    ASSISTANT = "assistant",
    FUNCTION = "function"
}

/**
 * Base class for chat messages
 */
export interface ChatMessage {
    /** Role of the message sender */
    role: MessageRole;
    /** Content of the message */
    content: string;
    /** Additional metadata */
    metadata: Record<string, any>;
}

/**
 * Message sent to request approval for a step
 */
export interface ApprovalRequest {
    /** Step identifier */
    step_id: string;
    /** Plan identifier */
    plan_id: string;
    /** Session identifier */
    session_id: string;
    /** User identifier */
    user_id: string;
    /** Action to be performed */
    action: string;
    /** Agent assigned to this step */
    agent: AgentType;
}

/**
 * Message containing human feedback on a step
 */
export interface HumanFeedback {
    /** Optional step identifier */
    step_id?: string;
    /** Plan identifier */
    plan_id: string;
    /** Session identifier */
    session_id: string;
    /** Whether the step is approved */
    approved: boolean;
    /** Optional feedback from human */
    human_feedback?: string;
    /** Optional updated action */
    updated_action?: string;
}

/**
 * Message containing human clarification on a plan
 */
export interface HumanClarification {
    /** Plan identifier */
    plan_id: string;
    /** Session identifier */
    session_id: string;
    /** Clarification from human */
    human_clarification: string;
}

/**
 * Message sent to an agent to perform an action
 */
export interface ActionRequest {
    /** Step identifier */
    step_id: string;
    /** Plan identifier */
    plan_id: string;
    /** Session identifier */
    session_id: string;
    /** Action to be performed */
    action: string;
    /** Agent assigned to this step */
    agent: AgentType;
}

/**
 * Message containing the response from an agent after performing an action
 */
export interface ActionResponse {
    /** Step identifier */
    step_id: string;
    /** Plan identifier */
    plan_id: string;
    /** Session identifier */
    session_id: string;
    /** Result of the action */
    result: string;
    /** Status after performing the action */
    status: StepStatus;
}

/**
 * Message for updating the plan state
 */
export interface PlanStateUpdate {
    /** Plan identifier */
    plan_id: string;
    /** Session identifier */
    session_id: string;
    /** Overall status of the plan */
    overall_status: PlanStatus;
}