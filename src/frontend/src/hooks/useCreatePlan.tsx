import { useCallback, useState } from "react";
import { TaskService } from "../services/TaskService";
import { ShowToastFn } from "../components/toast/InlineToaster";

export interface UseCreatePlanReturn {
    /** Whether a plan creation is in progress */
    submitting: boolean;
    /** Create a new plan and return the plan_id (or null on failure) */
    createPlan: (
        input: string,
        teamId?: string
    ) => Promise<string | null>;
}

/**
 * Hook that encapsulates the plan-creation API call, including
 * toast orchestration and error handling.
 *
 * @param showToast   - show a toast notification
 * @param dismissToast - dismiss a toast by id
 */
export function useCreatePlan(
    showToast: ShowToastFn,
    dismissToast: (id: any) => void
): UseCreatePlanReturn {
    const [submitting, setSubmitting] = useState<boolean>(false);

    const createPlan = useCallback(
        async (input: string, teamId?: string): Promise<string | null> => {
            if (!input.trim()) return null;

            setSubmitting(true);
            const id = showToast("Creating a plan", "progress");

            try {
                const response = await TaskService.createPlan(input.trim(), teamId);

                if (response.plan_id && response.plan_id !== null) {
                    showToast("Plan created!", "success");
                    dismissToast(id);
                    return response.plan_id;
                } else {
                    showToast("Failed to create plan", "error");
                    dismissToast(id);
                    return null;
                }
            } catch (error: any) {
                dismissToast(id);
                const errorMessage = error?.message || "Unable to create plan. Please try again.";
                showToast(errorMessage, "error");
                return null;
            } finally {
                setSubmitting(false);
            }
        },
        [showToast, dismissToast]
    );

    return { submitting, createPlan };
}

export default useCreatePlan;
