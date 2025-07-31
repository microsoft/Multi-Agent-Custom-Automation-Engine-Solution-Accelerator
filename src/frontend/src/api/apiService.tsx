import { apiClient } from './apiClient';
import {
    AgentMessage,
    HumanClarification,
    InputTask,
    InputTaskResponse,
    PlanWithSteps,
    Plan,
    Step,
    StepStatus,
    AgentType,
    PlanMessage
} from '../models';

// Constants for endpoints
const API_ENDPOINTS = {
    INPUT_TASK: '/input_task',
    PLANS: '/plans',
    STEPS: '/steps',
    HUMAN_FEEDBACK: '/human_feedback',
    APPROVE_STEPS: '/approve_step_or_steps',
    HUMAN_CLARIFICATION: '/human_clarification_on_plan',
    AGENT_MESSAGES: '/agent_messages',
    MESSAGES: '/messages',
    USER_BROWSER_LANGUAGE: '/user_browser_language'
};

// Simple cache implementation
interface CacheEntry<T> {
    data: T;
    timestamp: number;
    ttl: number; // Time to live in ms
}

class APICache {
    private cache: Map<string, CacheEntry<any>> = new Map();

    set<T>(key: string, data: T, ttl = 60000): void { // Default TTL: 1 minute
        this.cache.set(key, {
            data,
            timestamp: Date.now(),
            ttl
        });
    }

    get<T>(key: string): T | null {
        const entry = this.cache.get(key);
        if (!entry) return null;

        // Check if entry is expired
        if (Date.now() - entry.timestamp > entry.ttl) {
            this.cache.delete(key);
            return null;
        }

        return entry.data;
    }

    clear(): void {
        this.cache.clear();
    }

    invalidate(pattern: RegExp): void {
        for (const key of this.cache.keys()) {
            if (pattern.test(key)) {
                this.cache.delete(key);
            }
        }
    }
}

// Request tracking to prevent duplicate requests
class RequestTracker {
    private pendingRequests: Map<string, Promise<any>> = new Map();

    async trackRequest<T>(key: string, requestFn: () => Promise<T>): Promise<T> {
        // If request is already pending, return the existing promise
        if (this.pendingRequests.has(key)) {
            return this.pendingRequests.get(key)!;
        }

        // Create new request
        const requestPromise = requestFn();

        // Track the request
        this.pendingRequests.set(key, requestPromise);

        try {
            const result = await requestPromise;
            return result;
        } finally {
            // Remove from tracking when done (success or failure)
            this.pendingRequests.delete(key);
        }
    }
}

export class APIService {
    private _cache = new APICache();
    private _requestTracker = new RequestTracker();

    /**
     * Submit a new input task to generate a plan
     * @param inputTask The task description and optional session ID
     * @returns Promise with the response containing session and plan IDs
     */
    async submitInputTask(inputTask: InputTask): Promise<InputTaskResponse> {
        return apiClient.post(API_ENDPOINTS.INPUT_TASK, inputTask);
    }

    /**
     * Get all plans, optionally filtered by session ID
     * @param sessionId Optional session ID to filter plans
     * @param useCache Whether to use cached data or force fresh fetch
     * @returns Promise with array of plans with their steps
     */
    async getPlans(sessionId?: string, useCache = true): Promise<PlanWithSteps[]> {
        const cacheKey = `plans_${sessionId || 'all'}`;
        const params = sessionId ? { session_id: sessionId } : {};

        const fetcher = async () => {
            const data = await apiClient.get(API_ENDPOINTS.PLANS, { params });
            if (useCache) {
                this._cache.set(cacheKey, data, 30000); // Cache for 30 seconds
            }
            return data;
        };

        if (useCache) {
            return this._requestTracker.trackRequest(cacheKey, fetcher);
        }

        return fetcher();
    }

    /**
     * Get a single plan by plan ID
     * @param planId Plan ID to fetch
     * @param useCache Whether to use cached data or force fresh fetch
     * @returns Promise with the plan and its steps
     */
    async getPlanById(planId: string, useCache = true): Promise<{ plan_with_steps: PlanWithSteps; messages: PlanMessage[] }> {
        const cacheKey = `plan_by_id_${planId}`;
        const params = { plan_id: planId };

        const fetcher = async () => {
            const data = await apiClient.get(API_ENDPOINTS.PLANS, { params });

            // The API returns an array, but with plan_id filter it should have only one item
            if (!data) {
                throw new Error(`Plan with ID ${planId} not found`);
            }

            const plan = data[0] as PlanWithSteps;
            const messages = data[1] || [];
            if (useCache) {
                this._cache.set(cacheKey, { plan_with_steps: plan, messages }, 30000); // Cache for 30 seconds
            }
            return { plan_with_steps: plan, messages };
        };

        if (useCache) {
            const cachedPlan = this._cache.get<{ plan_with_steps: PlanWithSteps; messages: PlanMessage[] }>(cacheKey);
            if (cachedPlan) return cachedPlan;

            return this._requestTracker.trackRequest(cacheKey, fetcher);
        }

        return fetcher();
    }

    /**
     * Get a specific plan with its steps
     * @param sessionId Session ID
     * @param planId Plan ID
     * @param useCache Whether to use cached data or force fresh fetch
     * @returns Promise with the plan and its steps
     */
    async getPlanWithSteps(sessionId: string, planId: string, useCache = true): Promise<PlanWithSteps> {
        const cacheKey = `plan_${sessionId}_${planId}`;

        if (useCache) {
            const cachedPlan = this._cache.get<PlanWithSteps>(cacheKey);
            if (cachedPlan) return cachedPlan;
        }

        const fetcher = async () => {
            const plans = await this.getPlans(sessionId, useCache);
            const plan = plans.find(p => p.id === planId);

            if (!plan) {
                throw new Error(`Plan with ID ${planId} not found`);
            }

            if (useCache) {
                this._cache.set(cacheKey, plan, 30000); // Cache for 30 seconds
            }

            return plan;
        };

        if (useCache) {
            return this._requestTracker.trackRequest(cacheKey, fetcher);
        }

        return fetcher();
    }

    /**
     * Get steps for a specific plan
     * @param planId Plan ID
     * @param useCache Whether to use cached data or force fresh fetch
     * @returns Promise with array of steps
     */
    async getSteps(planId: string, useCache = true): Promise<Step[]> {
        const cacheKey = `steps_${planId}`;

        const fetcher = async () => {
            const data = await apiClient.get(`${API_ENDPOINTS.STEPS}/${planId}`);
            if (useCache) {
                this._cache.set(cacheKey, data, 30000); // Cache for 30 seconds
            }
            return data;
        };

        if (useCache) {
            return this._requestTracker.trackRequest(cacheKey, fetcher);
        }

        return fetcher();
    }

    /**
     * Update a step with new status and optional feedback
     * @param sessionId Session ID
     * @param planId Plan ID
     * @param stepId Step ID
     * @param update Update object with status and optional feedback
     * @returns Promise with the updated step
     */
    async updateStep(
        sessionId: string,
        planId: string,
        stepId: string,
        update: {
            status: StepStatus;
            human_feedback?: string;
            updated_action?: string;
        }
    ): Promise<Step> {
        const response = await this.provideStepFeedback(
            stepId,
            planId,
            sessionId,
            update.status === StepStatus.APPROVED,
            update.human_feedback,
            update.updated_action
        );

        // Invalidate cached data
        this._cache.invalidate(new RegExp(`^(plan|steps)_${planId}`));
        this._cache.invalidate(new RegExp(`^plans_`));

        // Get fresh step data
        const steps = await this.getSteps(planId, false); // Force fresh data
        const updatedStep = steps.find(step => step.id === stepId);

        if (!updatedStep) {
            throw new Error(`Step with ID ${stepId} not found after update`);
        }

        return updatedStep;
    }

    /**
     * Provide feedback for a specific step
     * @param stepId Step ID
     * @param planId Plan ID
     * @param sessionId Session ID
     * @param approved Whether the step is approved
     * @param humanFeedback Optional human feedback
     * @param updatedAction Optional updated action
     * @returns Promise with response object
     */
    async provideStepFeedback(
        stepId: string,
        planId: string,
        sessionId: string,
        approved: boolean,
        humanFeedback?: string,
        updatedAction?: string
    ): Promise<{ status: string; session_id: string; step_id: string }> {
        const response = await apiClient.post(
            API_ENDPOINTS.HUMAN_FEEDBACK,
            {
                step_id: stepId,
                plan_id: planId,
                session_id: sessionId,
                approved,
                human_feedback: humanFeedback,
                updated_action: updatedAction
            }
        );

        // Invalidate cached data
        this._cache.invalidate(new RegExp(`^(plan|steps)_${planId}`));
        this._cache.invalidate(new RegExp(`^plans_`));

        return response;
    }

    /**
     * Approve one or more steps
     * @param planId Plan ID
     * @param sessionId Session ID
     * @param approved Whether the step(s) are approved
     * @param stepId Optional specific step ID
     * @param humanFeedback Optional human feedback
     * @param updatedAction Optional updated action
     * @returns Promise with response object
     */
    async stepStatus(
        planId: string,
        sessionId: string,
        approved: boolean,
        stepId?: string,
    ): Promise<{ status: string }> {
        const response = await apiClient.post(
            API_ENDPOINTS.APPROVE_STEPS,
            {
                step_id: stepId,
                plan_id: planId,
                session_id: sessionId,
                approved
            }
        );

        // Invalidate cached data
        this._cache.invalidate(new RegExp(`^(plan|steps)_${planId}`));
        this._cache.invalidate(new RegExp(`^plans_`));

        return response;
    }

    /**
     * Submit clarification for a plan
     * @param planId Plan ID
     * @param sessionId Session ID
     * @param clarification Clarification text
     * @returns Promise with response object
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

        const response = await apiClient.post(
            API_ENDPOINTS.HUMAN_CLARIFICATION,
            clarificationData
        );

        // Invalidate cached data
        this._cache.invalidate(new RegExp(`^(plan|steps)_${planId}`));
        this._cache.invalidate(new RegExp(`^plans_`));

        return response;
    }

    /**
     * Get agent messages for a session
     * @param sessionId Session ID
     * @param useCache Whether to use cached data or force fresh fetch
     * @returns Promise with array of agent messages
     */
    async getAgentMessages(sessionId: string, useCache = true): Promise<AgentMessage[]> {
        const cacheKey = `agent_messages_${sessionId}`;

        const fetcher = async () => {
            const data = await apiClient.get(`${API_ENDPOINTS.AGENT_MESSAGES}/${sessionId}`);
            if (useCache) {
                this._cache.set(cacheKey, data, 30000); // Cache for 30 seconds
            }
            return data;
        };

        if (useCache) {
            return this._requestTracker.trackRequest(cacheKey, fetcher);
        }

        return fetcher();
    }

    /**
     * Delete all messages
     * @returns Promise with response object
     */
    async deleteAllMessages(): Promise<{ status: string }> {
        const response = await apiClient.delete(API_ENDPOINTS.MESSAGES);

        // Clear all cached data
        this._cache.clear();

        return response;
    }

    /**
     * Get all messages
     * @param useCache Whether to use cached data or force fresh fetch
     * @returns Promise with array of messages
     */
    async getAllMessages(useCache = true): Promise<any[]> {
        const cacheKey = 'all_messages';

        const fetcher = async () => {
            const data = await apiClient.get(API_ENDPOINTS.MESSAGES);
            if (useCache) {
                this._cache.set(cacheKey, data, 30000); // Cache for 30 seconds
            }
            return data;
        };

        if (useCache) {
            return this._requestTracker.trackRequest(cacheKey, fetcher);
        }

        return fetcher();
    }

    // Utility methods

    /**
     * Check if a plan is complete (all steps are completed or failed)
     * @param plan Plan with steps
     * @returns Boolean indicating if plan is complete
     */
    isPlanComplete(plan: PlanWithSteps): boolean {
        return plan.steps.every(step =>
            [StepStatus.COMPLETED, StepStatus.FAILED].includes(step.status)
        );
    }

    /**
     * Get steps that are awaiting human feedback
     * @param plan Plan with steps
     * @returns Array of steps awaiting feedback
     */
    getStepsAwaitingFeedback(plan: PlanWithSteps): Step[] {
        return plan.steps.filter(step => step.status === StepStatus.AWAITING_FEEDBACK);
    }    /**
     * Get steps assigned to a specific agent type
     * @param plan Plan with steps
     * @param agentType Agent type to filter by
     * @returns Array of steps for the specified agent
     */
    getStepsForAgent(plan: PlanWithSteps, agentType: AgentType): Step[] {
        return plan.steps.filter(step => step.agent === agentType);
    }

    /**
     * Clear all cached data
     */
    clearCache(): void {
        this._cache.clear();
    }

    /**
     * Get progress status counts for a plan
     * @param plan Plan with steps
     * @returns Object with counts for each step status
     */
    getPlanProgressStatus(plan: PlanWithSteps): Record<StepStatus, number> {
        const result = Object.values(StepStatus).reduce((acc, status) => {
            acc[status] = 0;
            return acc;
        }, {} as Record<StepStatus, number>);

        plan.steps.forEach(step => {
            result[step.status]++;
        });

        return result;
    }

    /**
     * Get completion percentage for a plan
     * @param plan Plan with steps
     * @returns Completion percentage (0-100)
     */
    getPlanCompletionPercentage(plan: PlanWithSteps): number {
        if (!plan.steps.length) return 0;

        const completedSteps = plan.steps.filter(
            step => [StepStatus.COMPLETED, StepStatus.FAILED].includes(step.status)
        ).length;

        return Math.round((completedSteps / plan.steps.length) * 100);
    }

    /**
     * Send the user's browser language to the backend
     * @returns Promise with response object
     */
    async sendUserBrowserLanguage(): Promise<{ status: string }> {
        const language = navigator.language || navigator.languages[0] || 'en';
        const response = await apiClient.post(API_ENDPOINTS.USER_BROWSER_LANGUAGE, {
            language
        });
        return response;
    }
}

// Export a singleton instance
export const apiService = new APIService();
