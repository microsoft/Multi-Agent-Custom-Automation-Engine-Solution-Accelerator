import { useCallback, useEffect } from "react";
import {
    ProcessedPlanData,
    PlanStatus,
} from "../models";
import { PlanDataService } from "../services/PlanDataService";
import {
    useAppDispatch,
    useAppSelector,
    selectPlanData,
    selectPlanLoading,
    selectPlanErrorLoading,
    setShowApprovalButtons,
    setWaitingForPlan,
    setContinueWithWebsocketFlow,
    setAgentMessages,
    setPlanApprovalRequest,
    setStreamingMessageBuffer,
    setShowBufferingText,
    setPlanData,
    setLoading,
    setErrorLoading,
    resetPlanSession,
} from "../store";

/**
 * Return type for the usePlanLoader hook
 */
export interface UsePlanLoaderReturn {
    /** The loaded plan data */
    planData: ProcessedPlanData | any;
    /** Whether the plan is currently loading */
    loading: boolean;
    /** Whether there was an error loading */
    errorLoading: boolean;
    /** Function to load/reload plan data */
    loadPlanData: (useCache?: boolean) => Promise<ProcessedPlanData | null>;
}

/**
 * Hook that encapsulates plan loading logic.
 *
 * Reads plan state from Redux via granular selectors and dispatches
 * slice actions directly — no callback props needed.
 *
 * Handles:
 * - Fetching plan data by planId
 * - Loading / error states
 * - Initial plan setup (approval buttons, WS flow, messages, mplan, streaming buffer)
 */
export function usePlanLoader(
    planId: string | undefined,
): UsePlanLoaderReturn {
    const dispatch = useAppDispatch();
    const planData = useAppSelector(selectPlanData);
    const loading = useAppSelector(selectPlanLoading);
    const errorLoading = useAppSelector(selectPlanErrorLoading);

    const loadPlanData = useCallback(
        async (useCache = true): Promise<ProcessedPlanData | null> => {
            if (!planId) return null;
            dispatch(resetPlanSession());
            dispatch(setLoading(true));
            try {
                const planResult = await PlanDataService.fetchPlanData(planId, useCache);

                if (planResult?.plan?.overall_status === PlanStatus.IN_PROGRESS) {
                    dispatch(setShowApprovalButtons(true));
                } else {
                    dispatch(setShowApprovalButtons(false));
                    dispatch(setWaitingForPlan(false));
                }
                if (planResult?.plan?.overall_status !== PlanStatus.COMPLETED) {
                    dispatch(setContinueWithWebsocketFlow(true));
                }
                if (planResult?.messages) {
                    dispatch(setAgentMessages(planResult.messages));
                }
                if (planResult?.mplan) {
                    dispatch(setPlanApprovalRequest(planResult.mplan));
                }
                if (planResult?.streaming_message && planResult.streaming_message.trim() !== "") {
                    dispatch(setStreamingMessageBuffer(planResult.streaming_message));
                    dispatch(setShowBufferingText(true));
                }
                dispatch(setPlanData(planResult));
                return planResult;
            } catch (err) {
                dispatch(setErrorLoading(true));
                dispatch(setPlanData(null));
                return null;
            } finally {
                dispatch(setLoading(false));
            }
        },
        [planId, dispatch]
    );

    // Auto-load on planId change
    useEffect(() => {
        const initializePlanLoading = async () => {
            if (!planId) {
                dispatch(resetPlanSession());
                dispatch(setErrorLoading(true));
                return;
            }
            try {
                await loadPlanData(false);
            } catch (err) {
                console.error("Failed to initialize plan loading:", err);
            }
        };
        initializePlanLoading();
    }, [planId, loadPlanData, dispatch]);

    return {
        planData,
        loading,
        errorLoading,
        loadPlanData,
    };
}
