import {
  PlanWithSteps,
  Step,
  AgentType,
  ProcessedPlanData,
  PlanMessage,
} from "@/models";
import { apiService } from "@/api";

/**
 * Service for processing and managing plan data operations
 */
export class PlanDataService {
  /**
   * Fetch plan details by plan ID and process the data
   * @param planId Plan ID to fetch
   * @returns Promise with processed plan data
   */
  static async fetchPlanData(
    planId: string,
    useCache: boolean
  ): Promise<ProcessedPlanData> {
    try {
      // Use optimized getPlanById method for better performance
      const planBody = await apiService.getPlanById(planId, useCache);
      return this.processPlanData(
        planBody.plan_with_steps,
        planBody.messages || []
      );
    } catch (error) {
      console.log("Failed to fetch plan data:", error);
      throw error;
    }
  }

  /**
   * Process plan data to extract agents, steps, and clarification status
   * @param plan PlanWithSteps object to process
   * @returns Processed plan data
   */
  static processPlanData(
    plan: PlanWithSteps,
    messages: PlanMessage[]
  ): ProcessedPlanData {
    // Extract unique agents from steps
    const uniqueAgents = new Set<AgentType>();
    plan.steps.forEach((step) => {
      if (step.agent) {
        uniqueAgents.add(step.agent);
      }
    });

    // Convert Set to Array for easier handling
    const agents = Array.from(uniqueAgents);

    // Get all steps
    const steps = plan.steps;

    // Check if human_clarification_request is not null
    const hasClarificationRequest =
      plan.human_clarification_request != null &&
      plan.human_clarification_request.trim().length > 0;
    const hasClarificationResponse =
      plan.human_clarification_response != null &&
      plan.human_clarification_response.trim().length > 0;
    const enableChat = hasClarificationRequest && !hasClarificationResponse;
    const enableStepButtons =
      (hasClarificationRequest && hasClarificationResponse) ||
      (!hasClarificationRequest && !hasClarificationResponse);
    return {
      plan,
      agents,
      steps,
      hasClarificationRequest,
      hasClarificationResponse,
      enableChat,
      enableStepButtons,
      messages,
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

  /**
   * Approve a plan step
   * @param step Step to approve
   * @returns Promise with API response
   */
  static async stepStatus(
    step: Step,
    action: boolean
  ): Promise<{ status: string }> {
    try {
      return apiService.stepStatus(
        step.plan_id,
        step.session_id,
        action, // approved
        step.id
      );
    } catch (error) {
      console.log("Failed to change step status:", error);
      throw error;
    }
  }

  /**
   * Submit human clarification for a plan
   * @param planId Plan ID
   * @param sessionId Session ID
   * @param clarification Clarification text
   * @returns Promise with API response
   */
  static async submitClarification(
    planId: string,
    sessionId: string,
    clarification: string
  ) {
    try {
      return apiService.submitClarification(planId, sessionId, clarification);
    } catch (error) {
      console.log("Failed to submit clarification:", error);
      throw error;
    }
  }
}
