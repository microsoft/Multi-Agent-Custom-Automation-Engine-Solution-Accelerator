/**
 * Enumerations used throughout the application
 */

/**
 * Enumeration of agent types.
 */
export enum AgentType {
    HUMAN = "Human_Agent",
    HR = "Hr_Agent",
    MARKETING = "Marketing_Agent",
    PROCUREMENT = "Procurement_Agent",
    PRODUCT = "Product_Agent",
    GENERIC = "Generic_Agent",
    TECH_SUPPORT = "Tech_Support_Agent",
    GROUP_CHAT_MANAGER = "Group_Chat_Manager",
    PLANNER = "Planner_Agent"
}

export enum role {
    user = "user",
    assistant = "assistant"
}
/**
 * Enumeration of possible statuses for a step.
 */
export enum StepStatus {
    PLANNED = "planned",
    AWAITING_FEEDBACK = "awaiting_feedback",
    APPROVED = "approved",
    REJECTED = "rejected",
    ACTION_REQUESTED = "action_requested",
    COMPLETED = "completed",
    FAILED = "failed"
}

/**
 * Enumeration of possible statuses for a plan.
 */
export enum PlanStatus {
    IN_PROGRESS = "in_progress",
    COMPLETED = "completed",
    FAILED = "failed"
}

/**
 * Enumeration of human feedback statuses.
 */
export enum HumanFeedbackStatus {
    REQUESTED = "requested",
    ACCEPTED = "accepted",
    REJECTED = "rejected"
}
