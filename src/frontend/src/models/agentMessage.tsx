import { Agent } from 'http';
import { BaseModel } from './plan';
import { AgentMessageType, AgentType, WebsocketMessageType } from './enums';

/**
 * Represents a message from an agent
 */
export interface AgentMessage extends BaseModel {
    /** The type of data model */
    data_type: "agent_message";
    /** Session identifier */
    session_id: string;
    /** Plan identifier */
    plan_id: string;
    /** Content of the message */
    content: string;
    /** Source of the message (e.g., agent type) */
    source: string;
    /** Optional step identifier associated with the message */
    step_id?: string;
}

export interface AgentMessageData {
    agent: string;
    agent_type: AgentMessageType;
    timestamp: number;
    steps: any[];
    next_steps: any[];
    content: string;
    raw_data: string;
}

/**
 * Message sent to HumanAgent to request approval for a step.
 * Corresponds to the Python AgentMessageResponse class.
 */
export interface AgentMessageResponse {

    /** Plan identifier */
    plan_id: string;
    /** Agent name or identifier */
    agent: string;
    /** Message content */
    content: string;
    /** Type of agent (Human or AI) */
    agent_type: AgentMessageType;
    is_final: boolean;
    /** Raw data associated with the message */
    raw_data: string;

    streaming_message: string;

}

export interface FinalMessage {
    type: WebsocketMessageType;
    content: string;
    status: string;
    timestamp: number | null;
    raw_data: any;
}

export interface StreamingMessage {
    type: WebsocketMessageType;
    agent: string;
    content: string;
    is_final: boolean;
    raw_data: any;
}