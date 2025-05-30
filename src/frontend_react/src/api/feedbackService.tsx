import { apiClient } from './apiClient';
import { HumanClarification } from '../models';

/**
 * Service for submitting human feedback and clarifications
 */
export const feedbackService = {
    /**
     * Submit human clarification on a plan
     * @param planId The ID of the plan
     * @param sessionId The session ID
     * @param clarification The clarification text
     * @returns Promise with status response
     */
    async submitClarification(
        planId: string,
        sessionId: string,
        clarification: string
    ): Promise<{ status: string; session_id: string }> {
        const clarificationData: HumanClarification = {
            plan_id: planId,
            session_id: sessionId,
            human_clarification: clarification
        };

        return apiClient.post<{ status: string; session_id: string }>(
            '/human_clarification_on_plan',
            clarificationData
        );
    }
};
