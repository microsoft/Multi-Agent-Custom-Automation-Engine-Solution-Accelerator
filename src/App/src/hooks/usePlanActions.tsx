/**
 * usePlanData — encapsulates fetching a plan by ID
 * and dispatching the result into the Redux store.
 * Uses createAsyncThunk (fetchPlanData) for automatic
 * pending / fulfilled / rejected lifecycle.
 *
 * P1: AbortController — cancels in-flight fetch when a new one starts
 * or when the component unmounts, preventing stale dispatches.
 */
import { useCallback, useEffect, useRef } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { ProcessedPlanData } from '@/models';
import {
    fetchPlanData,
    resetPlan,
} from '@/store/slices/planSlice';
import {
    setAgentMessages,
    resetChat,
} from '@/store/slices/chatSlice';
import {
    setStreamingMessageBuffer,
    setShowBufferingText,
    resetStreaming,
} from '@/store/slices/streamingSlice';
import { setWsConnected } from '@/store/slices/appSlice';

/** Return type of dispatch(createAsyncThunk()) — has .abort() */
type ThunkPromise = ReturnType<typeof fetchPlanData> extends (...args: any[]) => infer R ? R : never;

export function usePlanActions() {
    const dispatch = useAppDispatch();
    /** Ref holding the in-flight thunk promise so we can abort it */
    const fetchPromiseRef = useRef<ReturnType<ReturnType<typeof fetchPlanData>> | null>(null);

    /** Abort any in-flight fetch on unmount */
    useEffect(() => {
        return () => {
            fetchPromiseRef.current?.abort();
        };
    }, []);

    /** Reset every piece of plan-related state across all slices */
    const resetPlanVariables = useCallback(() => {
        dispatch(resetPlan());
        dispatch(resetChat());
        dispatch(resetStreaming());
        dispatch(setWsConnected(false));
    }, [dispatch]);

    /**
     * Fetch plan data from API via createAsyncThunk and hydrate cross-slice state.
     * The core plan state (planData, loading, errorLoading) is handled
     * automatically by extraReducers in planSlice.
     */
    const loadPlanData = useCallback(
        async (planId: string, useCache = true): Promise<ProcessedPlanData | null> => {
            /* P1: Cancel any previous in-flight fetch before starting a new one */
            fetchPromiseRef.current?.abort();

            resetPlanVariables();

            const promise = dispatch(fetchPlanData({ planId, useCache }));
            fetchPromiseRef.current = promise;

            const resultAction = await promise;

            if (fetchPlanData.fulfilled.match(resultAction)) {
                const planResult = resultAction.payload;

                // Hydrate cross-slice state that extraReducers can't reach
                if (planResult?.messages) {
                    dispatch(setAgentMessages(planResult.messages));
                }

                if (planResult?.streaming_message?.trim()) {
                    dispatch(setStreamingMessageBuffer(planResult.streaming_message));
                    dispatch(setShowBufferingText(true));
                }

                return planResult;
            }
            return null;
        },
        [dispatch, resetPlanVariables],
    );

    return { resetPlanVariables, loadPlanData };
}

export default usePlanActions;
