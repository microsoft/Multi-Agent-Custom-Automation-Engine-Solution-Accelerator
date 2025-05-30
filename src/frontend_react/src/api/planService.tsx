import { apiClient } from './apiClient';
import { Plan, PlanWithSteps, Step, StepStatus } from '../models';

/**
 * Service for interacting with Plans and Steps
 */
export const planService = {
    /**
     * Get all plans
     * @param sessionId Optional session ID to filter plans
     * @returns Promise with an array of plans with their steps
     */
    async getPlans(sessionId?: string): Promise<PlanWithSteps[]> {
        const params = sessionId ? { session_id: sessionId } : {};
        return apiClient.get<PlanWithSteps[]>('/plans', { params });
    },

    /**
     * Get steps for a specific plan
     * @param planId The ID of the plan
     * @returns Promise with an array of steps
     */
    async getSteps(planId: string): Promise<Step[]> {
        return apiClient.get<Step[]>(`/steps/${planId}`);
    },

    /**
     * Update step status and provide feedback
     * @param stepId Step identifier
     * @param planId Plan identifier
     * @param sessionId Session identifier
     * @param approved Whether the step is approved
     * @param humanFeedback Optional feedback from human
     * @param updatedAction Optional updated action
     * @returns Promise with status response
     */
    async provideStepFeedback(
        stepId: string,
        planId: string,
        sessionId: string,
        approved: boolean,
        humanFeedback?: string,
        updatedAction?: string
    ): Promise<{ status: string; session_id: string; step_id: string }> {
        return apiClient.post<{ status: string; session_id: string; step_id: string }>('/human_feedback', {
            step_id: stepId,
            plan_id: planId,
            session_id: sessionId,
            approved,
            human_feedback: humanFeedback,
            updated_action: updatedAction
        });
    },

    /**
     * Approve a step or multiple steps in a plan
     * @param planId Plan identifier
     * @param sessionId Session identifier
     * @param stepId Optional step ID (if not provided, approves all steps)
     * @param approved Whether the step(s) are approved
     * @param humanFeedback Optional feedback from human
     * @param updatedAction Optional updated action
     * @returns Promise with status response
     */
    async approveSteps(
        planId: string,
        sessionId: string,
        approved: boolean,
        stepId?: string,
        humanFeedback?: string,
        updatedAction?: string
    ): Promise<{ status: string }> {
        return apiClient.post<{ status: string }>('/approve_step_or_steps', {
            step_id: stepId,
            plan_id: planId,
            session_id: sessionId,
            approved,
            human_feedback: humanFeedback,
            updated_action: updatedAction
        });
    },

    /**
     * Delete all messages and plans across sessions
     * @returns Promise with status response
     */
    async deleteAllMessages(): Promise<{ status: string }> {
        return apiClient.delete<{ status: string }>('/messages');
    },

    /**
     * Get all messages across sessions
     * @returns Promise with all messages
     */
    async getAllMessages(): Promise<any[]> {
        return apiClient.get<any[]>('/messages');
    }
};
