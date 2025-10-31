import { apiClient } from './apiClient';
import {
    AgentMessage,
    HumanClarification,
    InputTask,
    InputTaskResponse,
    Plan,
    StepStatus,
    AgentType,
    PlanApprovalRequest,
    PlanApprovalResponse,
    AgentMessageData,
    MPlanData,
    AgentMessageBE,
    MPlanBE,
    TeamConfigurationBE,
    PlanFromAPI,
    AgentMessageResponse
} from '../models';

// Constants for endpoints
const API_ENDPOINTS = {
    PROCESS_REQUEST: '/v3/process_request',
    PLANS: '/v3/plans',
    PLAN: '/v3/plan',
    PLAN_APPROVAL: '/v3/plan_approval',
    HUMAN_CLARIFICATION: '/v3/user_clarification',
    USER_BROWSER_LANGUAGE: '/user_browser_language',
    AGENT_MESSAGE: '/v3/agent_message',
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
     * Create a new plan with RAI validation
     * @param inputTask The task description and optional session ID
     * @returns Promise with the response containing plan ID and status
     */
    // async createPlan(inputTask: InputTask): Promise<{ plan_id: string; status: string; session_id: string }> {
    //     return apiClient.post(API_ENDPOINTS.PROCESS_REQUEST, inputTask);
    // }

    async createPlan(inputTask: InputTask): Promise<InputTaskResponse> {
        return apiClient.post(API_ENDPOINTS.PROCESS_REQUEST, inputTask);
    }

    /**
     * Get all plans, optionally filtered by session ID
     * @param sessionId Optional session ID to filter plans
     * @param useCache Whether to use cached data or force fresh fetch
     * @returns Promise with array of plans with their steps
     */
    async getPlans(sessionId?: string, useCache = true): Promise<Plan[]> {
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
    async getPlanById(planId: string, useCache = true): Promise<PlanFromAPI> {
        const cacheKey = `plan_by_id_${planId}`;
        const params = { plan_id: planId };

        const fetcher = async () => {
            const data = await apiClient.get(API_ENDPOINTS.PLAN, { params });

            // The API returns an array, but with plan_id filter it should have only one item
            if (!data) {
                throw new Error(`Plan with ID ${planId} not found`);
            }
            console.log('Fetched plan by ID:', data);
            const results = {
                plan: data.plan as Plan,
                messages: data.messages as AgentMessageBE[],
                m_plan: data.m_plan as MPlanBE | null,
                team: data.team as TeamConfigurationBE | null,
                streaming_message: data.streaming_message as string | null
            } as PlanFromAPI;
            if (useCache) {
                this._cache.set(cacheKey, results, 30000); // Cache for 30 seconds
            }
            return results;
        };

        if (useCache) {
            const cachedPlan = this._cache.get<PlanFromAPI>(cacheKey);
            if (cachedPlan) return cachedPlan;

            return this._requestTracker.trackRequest(cacheKey, fetcher);
        }

        return fetcher();
    }


    /**
   * Approve a plan for execution 
   * @param planApprovalData Plan approval data
   * @returns Promise with approval response
   */
    async approvePlan(planApprovalData: PlanApprovalRequest): Promise<PlanApprovalResponse> {
        const requestKey = `approve-plan-${planApprovalData.m_plan_id}`;

        return this._requestTracker.trackRequest(requestKey, async () => {
            console.log('📤 Approving plan via v3 API:', planApprovalData);

            const response = await apiClient.post(API_ENDPOINTS.PLAN_APPROVAL, planApprovalData);

            // Invalidate cache since plan execution will start
            this._cache.invalidate(new RegExp(`^plans_`));
            if (planApprovalData.plan_id) {
                this._cache.invalidate(new RegExp(`^plan.*_${planApprovalData.plan_id}`));
            }

            console.log('✅ Plan approval successful:', response);
            return response;
        });
    }


    /**
     * Submit clarification for a plan
     * @param planId Plan ID
     * @param sessionId Session ID
     * @param clarification Clarification text
     * @returns Promise with response object
     */
    async submitClarification(
        request_id: string = "",
        answer: string = "",
        plan_id: string = "",
        m_plan_id: string = ""
    ): Promise<{ status: string; session_id: string }> {
        const clarificationData: HumanClarification = {
            request_id,
            answer,
            plan_id,
            m_plan_id
        };

        const response = await apiClient.post(
            API_ENDPOINTS.HUMAN_CLARIFICATION,
            clarificationData
        );

        // Invalidate cached data
        this._cache.invalidate(new RegExp(`^(plan|steps)_${plan_id}`));
        this._cache.invalidate(new RegExp(`^plans_`));

        return response;
    }


    /**
     * Clear all cached data
     */
    clearCache(): void {
        this._cache.clear();
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
    async sendAgentMessage(data: AgentMessageResponse): Promise<AgentMessage> {
        const t0 = performance.now();
        const result = await apiClient.post(API_ENDPOINTS.AGENT_MESSAGE, data);
        console.log('[agent_message] sent', {
            ms: +(performance.now() - t0).toFixed(1),
            agent: data.agent,
            type: data.agent_type
        });
        return result;
    }
}

// Export a singleton instance
export const apiService = new APIService();
