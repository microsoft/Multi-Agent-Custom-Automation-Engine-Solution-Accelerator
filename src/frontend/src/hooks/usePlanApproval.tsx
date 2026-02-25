import { useCallback } from "react";
import { apiService } from "../api/apiService";
import { ShowToastFn } from "../components/toast/InlineToaster";
import {
    useAppDispatch,
    useAppSelector,
    selectPlanApprovalRequest,
    selectPlanData,
    selectProcessingApproval,
    selectShowApprovalButtons,
    handleApprovalStarted,
    handleApprovalCompleted,
    setProcessingApproval,
    setShowApprovalButtons,
} from "../store";

/**
 * Return type for the usePlanApproval hook
 */
export interface UsePlanApprovalReturn {
    /** Whether an approval/rejection is currently being processed */
    processingApproval: boolean;
    /** Whether approval buttons should be shown */
    showApprovalButtons: boolean;
    /** Approve the plan */
    handleApprovePlan: () => Promise<void>;
    /** Reject the plan */
    handleRejectPlan: () => Promise<void>;
}

/**
 * Hook that encapsulates plan approval and rejection logic.
 *
 * Reads planApprovalRequest and planData from Redux via granular selectors
 * and dispatches compound actions (handleApprovalStarted / handleApprovalCompleted).
 *
 * @param showToast   - toast notification function
 * @param dismissToast - dismiss a specific toast
 * @param navigate     - router navigation function
 */
export function usePlanApproval(
    showToast: ShowToastFn,
    dismissToast: (id: any) => void,
    navigate: (path: string) => void,
): UsePlanApprovalReturn {
    const dispatch = useAppDispatch();
    const planApprovalRequest = useAppSelector(selectPlanApprovalRequest);
    const planData = useAppSelector(selectPlanData);
    const processingApproval = useAppSelector(selectProcessingApproval);
    const showApprovalButtons = useAppSelector(selectShowApprovalButtons);

    const handleApprovePlan = useCallback(async () => {
        if (!planApprovalRequest) return;

        dispatch(handleApprovalStarted());
        const id = showToast("Submitting Approval", "progress");

        try {
            await apiService.approvePlan({
                m_plan_id: planApprovalRequest.id,
                plan_id: planData?.plan?.id || "",
                approved: true,
                feedback: "Plan approved by user",
            });

            dismissToast(id);
            dispatch(handleApprovalCompleted());
        } catch (error) {
            dismissToast(id);
            showToast("Failed to submit approval", "error");
            dispatch(setProcessingApproval(false));
        }
    }, [planApprovalRequest, planData, showToast, dismissToast, dispatch]);

    const handleRejectPlan = useCallback(async () => {
        if (!planApprovalRequest) return;

        dispatch(handleApprovalStarted());
        const id = showToast("Submitting cancellation", "progress");
        try {
            await apiService.approvePlan({
                m_plan_id: planApprovalRequest.id,
                plan_id: planData?.plan?.id || "",
                approved: false,
                feedback: "Plan rejected by user",
            });
            dismissToast(id);
            navigate("/");
        } catch (error) {
            dismissToast(id);
            showToast("Failed to submit cancellation", "error");
            navigate("/");
        } finally {
            dispatch(setProcessingApproval(false));
        }
    }, [planApprovalRequest, planData, navigate, showToast, dismissToast, dispatch]);

    return {
        processingApproval,
        showApprovalButtons,
        handleApprovePlan,
        handleRejectPlan,
    };
}
