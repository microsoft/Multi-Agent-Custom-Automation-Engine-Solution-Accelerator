import { PlanWithSteps, Step, AgentType } from '@/models';
import { apiService } from '@/api';

/**
 * Interface for processed plan data
 */
export interface ProcessedPlanData {
    plan: PlanWithSteps;
    agents: AgentType[];
    steps: Step[];
    hasHumanClarificationRequest: boolean;
}

/**
 * Service for processing and managing plan data operations
 */
export class PlanDataService {    /**
     * Fetch plan details by plan ID and process the data
     * @param planId Plan ID to fetch
     * @returns Promise with processed plan data
     */
    static async fetchPlanData(planId: string): Promise<ProcessedPlanData> {
        try {
            // Use optimized getPlanById method for better performance
            const plan = await apiService.getPlanById(planId);
            return this.processPlanData(plan);
        } catch (error) {
            console.error('Failed to fetch plan data:', error);
            throw error;
        }
    }

    /**
     * Process plan data to extract agents, steps, and clarification status
     * @param plan PlanWithSteps object to process
     * @returns Processed plan data
     */
    static processPlanData(plan: PlanWithSteps): ProcessedPlanData {
        // Extract unique agents from steps
        const uniqueAgents = new Set<AgentType>();
        plan.steps.forEach(step => {
            if (step.agent) {
                uniqueAgents.add(step.agent);
            }
        });

        // Convert Set to Array for easier handling
        const agents = Array.from(uniqueAgents);

        // Get all steps
        const steps = plan.steps;

        // Check if human_clarification_request is not null
        const hasHumanClarificationRequest = plan.human_clarification_request != null &&
            plan.human_clarification_request.trim().length > 0;

        return {
            plan,
            agents,
            steps,
            hasHumanClarificationRequest
        };
    }

    /**
     * Get steps for a specific agent type
     * @param plan Plan with steps
     * @param agentType Agent type to filter by
     * @returns Array of steps for the specified agent
     */
    static getStepsForAgent(plan: PlanWithSteps, agentType: AgentType): Step[] {
        return apiService.getStepsForAgent(plan, agentType);
    }

    /**
     * Get steps that are awaiting human feedback
     * @param plan Plan with steps
     * @returns Array of steps awaiting feedback
     */
    static getStepsAwaitingFeedback(plan: PlanWithSteps): Step[] {
        return apiService.getStepsAwaitingFeedback(plan);
    }

    /**
     * Check if plan is complete
     * @param plan Plan with steps
     * @returns Boolean indicating if plan is complete
     */
    static isPlanComplete(plan: PlanWithSteps): boolean {
        return apiService.isPlanComplete(plan);
    }

    /**
     * Get plan completion percentage
     * @param plan Plan with steps
     * @returns Completion percentage (0-100)
     */
    static getPlanCompletionPercentage(plan: PlanWithSteps): number {
        return apiService.getPlanCompletionPercentage(plan);
    }
}
