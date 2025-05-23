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
    AgentType
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
    MESSAGES: '/messages'
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

        return entry.data as T;
    } invalidate(keyPattern: RegExp | string): void {
        if (typeof keyPattern === 'string') {
            this.cache.delete(keyPattern);
            return;
        }

        // If RegExp, delete all matching keys
        // Use Array.from to avoid iterator compatibility issues
        Array.from(this.cache.keys()).forEach(key => {
            if (keyPattern.test(key)) {
                this.cache.delete(key);
            }
        });
    }

    clear(): void {
        this.cache.clear();
    }
}

/**
 * Unified API service for interacting with the backend app_kernel.py
 */
export const apiService = {
    // Cache instance
    _cache: new APICache(),

    // API request tracking
    _requestsInProgress: new Map<string, Promise<any>>(),

    /**
     * Track API calls to prevent duplicate requests for the same resource
     * @param key Unique identifier for this request
     * @param request Promise function that makes the actual API call
     */
    async _trackRequest<T>(key: string, request: () => Promise<T>): Promise<T> {
        // Check if request is already in progress
        if (this._requestsInProgress.has(key)) {
            return this._requestsInProgress.get(key);
        }

        // Check cache first
        const cachedData = this._cache.get<T>(key);
        if (cachedData) return cachedData;

        // Make the request and track it
        const promise = request().finally(() => {
            this._requestsInProgress.delete(key);
        });

        this._requestsInProgress.set(key, promise);
        return promise;
    },

    // Task-related methods
    /**
     * Submit a new input task to generate a plan
     * @param inputTask The task description and optional session ID
     * @returns Promise with the response containing session and plan IDs
     */
    async submitInputTask(inputTask: InputTask): Promise<InputTaskResponse> {
        return apiClient.post<InputTaskResponse>(API_ENDPOINTS.INPUT_TASK, inputTask);
    },

    // Plan-related methods
    /**
     * Get all plans
     * @param sessionId Optional session ID to filter plans
     * @param useCache Whether to use cached data if available
     * @returns Promise with an array of plans with their steps
     */
    async getPlans(sessionId?: string, useCache = true): Promise<PlanWithSteps[]> {
        const cacheKey = `plans_${sessionId || 'all'}`;
        const params = sessionId ? { session_id: sessionId } : {};

        const fetcher = async () => {
            const data = await apiClient.get<PlanWithSteps[]>(API_ENDPOINTS.PLANS, { params });
            if (useCache) {
                this._cache.set(cacheKey, data, 30000); // Cache for 30 seconds
            }
            return data;
        };

        if (useCache) {
            return this._trackRequest<PlanWithSteps[]>(cacheKey, fetcher);
        }

        return fetcher();
    },

    /**
     * Get plan with steps by session ID and plan ID
     * @param sessionId The session ID
     * @param planId The plan ID
     * @param useCache Whether to use cached data if available
     * @returns Promise with the plan and its steps
     */
    async getPlanWithSteps(sessionId: string, planId: string, useCache = true): Promise<PlanWithSteps> {
        const cacheKey = `plan_${sessionId}_${planId}`;

        // Check cache first if enabled
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
            return this._trackRequest<PlanWithSteps>(cacheKey, fetcher);
        }

        return fetcher();
    },

    /**
     * Get steps for a specific plan
     * @param planId The ID of the plan
     * @param useCache Whether to use cached data if available
     * @returns Promise with an array of steps
     */
    async getSteps(planId: string, useCache = true): Promise<Step[]> {
        const cacheKey = `steps_${planId}`;

        const fetcher = async () => {
            const data = await apiClient.get<Step[]>(`${API_ENDPOINTS.STEPS}/${planId}`);
            if (useCache) {
                this._cache.set(cacheKey, data, 30000); // Cache for 30 seconds
            }
            return data;
        };

        if (useCache) {
            return this._trackRequest<Step[]>(cacheKey, fetcher);
        }

        return fetcher();
    },

    /**
     * Update a step
     * @param sessionId Session identifier
     * @param planId Plan identifier
     * @param stepId Step identifier
     * @param update The update to apply to the step
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

        // Invalidate caches for this plan and its steps
        this._cache.invalidate(new RegExp(`^(plan|steps)_${planId}`));
        this._cache.invalidate(new RegExp(`^plans_`));

        // Get the updated step after providing feedback
        const steps = await this.getSteps(planId, false); // Force fresh data
        const updatedStep = steps.find(step => step.id === stepId);
        if (!updatedStep) {
            throw new Error(`Step with ID ${stepId} not found after update`);
        }
        return updatedStep;
    },

    // Feedback-related methods
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
        const response = await apiClient.post<{ status: string; session_id: string; step_id: string }>(
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

        // Invalidate related caches
        this._cache.invalidate(new RegExp(`^(plan|steps)_${planId}`));
        this._cache.invalidate(new RegExp(`^plans_`));

        return response;
    },

    /**
     * Approve a step or multiple steps in a plan
     * @param planId Plan identifier
     * @param sessionId Session identifier
     * @param approved Whether the step(s) are approved
     * @param stepId Optional step ID (if not provided, approves all steps)
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
        const response = await apiClient.post<{ status: string }>(
            API_ENDPOINTS.APPROVE_STEPS,
            {
                step_id: stepId,
                plan_id: planId,
                session_id: sessionId,
                approved,
                human_feedback: humanFeedback,
                updated_action: updatedAction
            }
        );

        // Invalidate related caches
        this._cache.invalidate(new RegExp(`^(plan|steps)_${planId}`));
        this._cache.invalidate(new RegExp(`^plans_`));

        return response;
    },

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

        const response = await apiClient.post<{ status: string; session_id: string }>(
            API_ENDPOINTS.HUMAN_CLARIFICATION,
            clarificationData
        );

        // Invalidate related caches
        this._cache.invalidate(new RegExp(`^(plan|steps)_${planId}`));
        this._cache.invalidate(new RegExp(`^plans_`));

        return response;
    },

    // Message-related methods
    /**
     * Get all agent messages for a specific session
     * @param sessionId The session ID
     * @param useCache Whether to use cached data if available
     * @returns Promise with an array of agent messages
     */
    async getAgentMessages(sessionId: string, useCache = true): Promise<AgentMessage[]> {
        const cacheKey = `agent_messages_${sessionId}`;

        const fetcher = async () => {
            const data = await apiClient.get<AgentMessage[]>(`${API_ENDPOINTS.AGENT_MESSAGES}/${sessionId}`);
            if (useCache) {
                this._cache.set(cacheKey, data, 30000); // Cache for 30 seconds
            }
            return data;
        };

        if (useCache) {
            return this._trackRequest<AgentMessage[]>(cacheKey, fetcher);
        }

        return fetcher();
    },

    /**
     * Delete all messages and plans across sessions
     * @returns Promise with status response
     */
    async deleteAllMessages(): Promise<{ status: string }> {
        const response = await apiClient.delete<{ status: string }>(API_ENDPOINTS.MESSAGES);

        // Clear the entire cache since everything is deleted
        this._cache.clear();

        return response;
    },

    /**
     * Get all messages across sessions
     * @param useCache Whether to use cached data if available
     * @returns Promise with all messages
     */
    async getAllMessages(useCache = true): Promise<any[]> {
        const cacheKey = 'all_messages';

        const fetcher = async () => {
            const data = await apiClient.get<any[]>(API_ENDPOINTS.MESSAGES);
            if (useCache) {
                this._cache.set(cacheKey, data, 30000); // Cache for 30 seconds
            }
            return data;
        };

        if (useCache) {
            return this._trackRequest<any[]>(cacheKey, fetcher);
        }

        return fetcher();
    },

    // Utility methods
    /**
     * Check if a plan has completed all steps
     * @param plan The plan to check
     * @returns true if all steps are completed or failed
     */
    isPlanComplete(plan: PlanWithSteps): boolean {
        return plan.steps.every(
            step => step.status === StepStatus.COMPLETED || step.status === StepStatus.FAILED
        );
    },

    /**
     * Get steps that are awaiting feedback for a plan
     * @param plan The plan to check
     * @returns Array of steps awaiting feedback
     */
    getStepsAwaitingFeedback(plan: PlanWithSteps): Step[] {
        return plan.steps.filter(
            step => step.status === StepStatus.AWAITING_FEEDBACK
        );
    },

    /**
     * Get steps assigned to a specific agent
     * @param plan The plan containing steps
     * @param agentType The type of agent to filter by
     * @returns Array of steps assigned to the specified agent
     */
    getStepsForAgent(plan: PlanWithSteps, agentType: AgentType): Step[] {
        return plan.steps.filter(step => step.agent === agentType);
    },

    /**
     * Force refresh all cached data
     */
    clearCache(): void {
        this._cache.clear();
    },

    /**
     * Get detailed progress status for a plan
     * @param plan The plan to analyze
     * @returns Object with counts of steps in each status
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
    },

    /**
     * Calculate the overall completion percentage of a plan
     * @param plan The plan to calculate completion for
     * @returns Percentage of completion from 0 to 100
     */
    getPlanCompletionPercentage(plan: PlanWithSteps): number {
        if (!plan.steps.length) return 0;

        const completedSteps = plan.steps.filter(
            step => [StepStatus.COMPLETED, StepStatus.FAILED].includes(step.status)
        ).length;

        return Math.round((completedSteps / plan.steps.length) * 100);
    }
};

export default apiService;
