import { useState, useEffect, useCallback } from 'react';
import { PlanWithSteps, Step, HumanFeedbackStatus, StepStatus } from '../models';
import { apiService } from '../api/apiService';

/**
 * Custom hook for working with a plan and its steps
 * 
 * @param sessionId The session ID
 * @param planId The plan ID
 * @returns Object containing plan data, loading state, error state, and functions to interact with the plan
 */
export const usePlan = (sessionId: string, planId: string) => {
    const [planWithSteps, setPlanWithSteps] = useState<PlanWithSteps | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<Error | null>(null);

    /**
     * Fetch the plan and its steps
     */
    const fetchPlan = useCallback(async (forceRefresh = false) => {
        try {
            setLoading(true);
            const data = await apiService.getPlanWithSteps(sessionId, planId, !forceRefresh);
            setPlanWithSteps(data);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Failed to fetch plan'));
        } finally {
            setLoading(false);
        }
    }, [sessionId, planId]);

    /**
     * Update a step's status and provide feedback
     * 
     * @param stepId The step ID
     * @param approved Whether the step is approved
     * @param feedback Optional feedback message
     * @param updatedAction Optional updated action
     * @returns Promise resolving to the updated step
     */
    const updateStepFeedback = useCallback(async (
        stepId: string,
        approved: boolean,
        feedback?: string,
        updatedAction?: string
    ) => {
        try {
            const status = approved ? StepStatus.APPROVED : StepStatus.REJECTED;

            const update = {
                status,
                human_feedback: feedback,
                updated_action: updatedAction
            };

            const updatedStep = await apiService.updateStep(sessionId, planId, stepId, update);

            // Update local state
            if (planWithSteps) {
                const updatedSteps = planWithSteps.steps.map(step =>
                    step.id === stepId ? { ...step, ...updatedStep } : step
                );

                setPlanWithSteps({
                    ...planWithSteps,
                    steps: updatedSteps
                });
            }

            return updatedStep;
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Failed to update step'));
            throw err;
        }
    }, [sessionId, planId, planWithSteps]);

    /**
     * Get steps that are awaiting feedback
     * 
     * @returns Array of steps awaiting feedback
     */
    const getStepsAwaitingFeedback = useCallback((): Step[] => {
        if (!planWithSteps) return [];
        return planWithSteps.steps.filter(
            step => step.status === StepStatus.AWAITING_FEEDBACK &&
                step.human_approval_status === HumanFeedbackStatus.REQUESTED
        );
    }, [planWithSteps]);

    /**
     * Check if the plan is complete
     * 
     * @returns Boolean indicating if all steps are completed or failed
     */
    const isPlanComplete = useCallback((): boolean => {
        if (!planWithSteps) return false;
        return apiService.isPlanComplete(planWithSteps);
    }, [planWithSteps]);

    // Initial fetch
    useEffect(() => {
        if (sessionId && planId) {
            fetchPlan();
        }
    }, [sessionId, planId, fetchPlan]);

    return {
        plan: planWithSteps,
        loading,
        error,
        fetchPlan,
        updateStepFeedback,
        getStepsAwaitingFeedback,
        isPlanComplete
    };
};

export default usePlan;
