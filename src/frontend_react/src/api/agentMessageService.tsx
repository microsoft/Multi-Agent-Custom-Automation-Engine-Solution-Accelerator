import { apiClient } from './apiClient';
import { AgentMessage } from '../models';

/**
 * Service for interacting with agent messages
 */
export const agentMessageService = {
    /**
     * Get all agent messages for a specific session
     * @param sessionId The session ID
     * @returns Promise with an array of agent messages
     */
    async getAgentMessages(sessionId: string): Promise<AgentMessage[]> {
        return apiClient.get<AgentMessage[]>(`/agent_messages/${sessionId}`);
    }
};
