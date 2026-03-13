/**
 * Plan Slice — centralises all plan-level state that was previously
 * scattered across 10+ useState calls in PlanPage.
 */
import { createSlice, createAsyncThunk, createSelector, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../store';
import { ProcessedPlanData, MPlanData, PlanStatus } from '@/models';
import { PlanDataService } from '@/services/PlanDataService';

/* ── Async Thunks (Point 9 — createAsyncThunk for API‑driven state) ── */

/**
 * Fetch plan data from the API by planId.
 * Automatically dispatches pending / fulfilled / rejected actions
 * that are handled in extraReducers below.
 */
export const fetchPlanData = createAsyncThunk<
    ProcessedPlanData | null,
    { planId: string; useCache?: boolean },
    { rejectValue: string }
>(
    'plan/fetchPlanData',
    async ({ planId, useCache = true }, { rejectWithValue }) => {
        try {
            return await PlanDataService.fetchPlanData(planId, useCache);
        } catch {
            return rejectWithValue('Failed to load plan data');
        }
    },
);

export interface PlanState {
    /** Fully processed plan (null when not loaded) */
    planData: ProcessedPlanData | null;
    /** Is the initial plan load in flight? */
    loading: boolean;
    /** Did the plan load fail? */
    errorLoading: boolean;
    /** Waiting for the backend to produce a plan */
    waitingForPlan: boolean;
    /** Plan-approval payload received from WebSocket */
    planApprovalRequest: MPlanData | null;
    /** Is an approval/reject API call in progress? */
    processingApproval: boolean;
    /** Should the approval buttons be visible? */
    showApprovalButtons: boolean;
    /** Show a spinner while the plan is being executed */
    showProcessingPlanSpinner: boolean;
    /** Should we continue with WebSocket flow? */
    continueWithWebsocketFlow: boolean;
    /** Has the user approved the plan (or is the plan already post-approval)? */
    planApproved: boolean;
    /** Trigger to reload the left-panel task list */
    reloadLeftList: boolean;
    /** Cancellation dialog state */
    showCancellationDialog: boolean;
    /** Is a cancellation API call in progress? */
    cancellingPlan: boolean;
    /** Loading message for spinners */
    loadingMessage: string;
}

const initialState: PlanState = {
    planData: null,
    loading: true,
    errorLoading: false,
    waitingForPlan: true,
    planApprovalRequest: null,
    processingApproval: false,
    showApprovalButtons: true,
    showProcessingPlanSpinner: false,
    continueWithWebsocketFlow: false,
    planApproved: false,
    reloadLeftList: true,
    showCancellationDialog: false,
    cancellingPlan: false,
    loadingMessage: '',
};

const planSlice = createSlice({
    name: 'plan',
    initialState,
    reducers: {
        setPlanData(state, action: PayloadAction<ProcessedPlanData | null>) {
            state.planData = action.payload as any;
        },
        setLoading(state, action: PayloadAction<boolean>) {
            state.loading = action.payload;
        },
        setErrorLoading(state, action: PayloadAction<boolean>) {
            state.errorLoading = action.payload;
        },
        setWaitingForPlan(state, action: PayloadAction<boolean>) {
            state.waitingForPlan = action.payload;
        },
        setPlanApprovalRequest(state, action: PayloadAction<MPlanData | null>) {
            state.planApprovalRequest = action.payload as any;
        },
        setProcessingApproval(state, action: PayloadAction<boolean>) {
            state.processingApproval = action.payload;
        },
        setShowApprovalButtons(state, action: PayloadAction<boolean>) {
            state.showApprovalButtons = action.payload;
        },
        setShowProcessingPlanSpinner(state, action: PayloadAction<boolean>) {
            state.showProcessingPlanSpinner = action.payload;
        },
        setContinueWithWebsocketFlow(state, action: PayloadAction<boolean>) {
            state.continueWithWebsocketFlow = action.payload;
        },
        setPlanApproved(state, action: PayloadAction<boolean>) {
            state.planApproved = action.payload;
        },
        setReloadLeftList(state, action: PayloadAction<boolean>) {
            state.reloadLeftList = action.payload;
        },
        setShowCancellationDialog(state, action: PayloadAction<boolean>) {
            state.showCancellationDialog = action.payload;
        },
        setCancellingPlan(state, action: PayloadAction<boolean>) {
            state.cancellingPlan = action.payload;
        },
        setLoadingMessage(state, action: PayloadAction<string>) {
            state.loadingMessage = action.payload;
        },
        /** Mark plan completed and update local state in one dispatch */
        markPlanCompleted(state) {
            if (state.planData?.plan) {
                (state.planData as any).plan.overall_status = PlanStatus.COMPLETED;
            }
        },

        /* ── Compound Actions (Optimization — batch multiple state changes) ── */

        /** Single dispatch after user approves a plan (replaces 4 separate dispatches) */
        planApprovalAccepted(state) {
            state.planApproved = true;
            state.showApprovalButtons = false;
            state.showProcessingPlanSpinner = true;
            state.processingApproval = false;
        },
        /** Single dispatch after user rejects a plan (replaces 3 separate dispatches) */
        planApprovalRejected(state) {
            state.planApproved = false;
            state.showApprovalButtons = false;
            state.showProcessingPlanSpinner = false;
            state.processingApproval = false;
        },
        /** Single dispatch when PLAN_APPROVAL_REQUEST arrives via WebSocket */
        approvalRequestReceived(state, action: PayloadAction<MPlanData>) {
            state.planApprovalRequest = action.payload as any;
            state.waitingForPlan = false;
            state.showProcessingPlanSpinner = false;
            state.showApprovalButtons = true;
        },
        /** Single dispatch when FINAL_RESULT_MESSAGE arrives and plan is complete */
        planCompletedFinal(state) {
            state.showProcessingPlanSpinner = false;
            if (state.planData?.plan) {
                (state.planData as any).plan.overall_status = PlanStatus.COMPLETED;
            }
        },

        /** Reset everything back to initial state (used when navigating to a new plan) */
        resetPlan() {
            return { ...initialState };
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchPlanData.pending, (state) => {
                state.loading = true;
                state.errorLoading = false;
            })
            .addCase(fetchPlanData.fulfilled, (state, action) => {
                const planResult = action.payload;
                state.loading = false;

                if (planResult?.plan?.overall_status === PlanStatus.IN_PROGRESS) {
                    state.showApprovalButtons = true;
                } else {
                    state.showApprovalButtons = false;
                    state.waitingForPlan = false;
                }

                if (planResult?.plan?.overall_status !== PlanStatus.COMPLETED) {
                    state.continueWithWebsocketFlow = true;
                }

                // Mark plan as already approved if it's past the approval stage
                if (
                    planResult?.plan?.overall_status === PlanStatus.APPROVED ||
                    planResult?.plan?.overall_status === PlanStatus.COMPLETED
                ) {
                    state.planApproved = true;
                }

                if (planResult?.mplan) {
                    state.planApprovalRequest = planResult.mplan as any;
                }

                state.planData = planResult as any;
            })
            .addCase(fetchPlanData.rejected, (state) => {
                state.loading = false;
                state.errorLoading = true;
                state.planData = null;
            });
    },
});

export const {
    setPlanData,
    setLoading,
    setErrorLoading,
    setWaitingForPlan,
    setPlanApprovalRequest,
    setProcessingApproval,
    setShowApprovalButtons,
    setShowProcessingPlanSpinner,
    setContinueWithWebsocketFlow,
    setPlanApproved,
    setReloadLeftList,
    setShowCancellationDialog,
    setCancellingPlan,
    setLoadingMessage,
    markPlanCompleted,
    planApprovalAccepted,
    planApprovalRejected,
    approvalRequestReceived,
    planCompletedFinal,
    resetPlan,
} = planSlice.actions;

/* ── Granular Selectors (Point 10) ────────────────────────────────── */
export const selectPlanData = (s: RootState) => s.plan.planData;
export const selectPlanLoading = (s: RootState) => s.plan.loading;
export const selectErrorLoading = (s: RootState) => s.plan.errorLoading;
export const selectWaitingForPlan = (s: RootState) => s.plan.waitingForPlan;
export const selectPlanApprovalRequest = (s: RootState) => s.plan.planApprovalRequest;
export const selectProcessingApproval = (s: RootState) => s.plan.processingApproval;
export const selectShowApprovalButtons = (s: RootState) => s.plan.showApprovalButtons;
export const selectShowProcessingPlanSpinner = (s: RootState) => s.plan.showProcessingPlanSpinner;
export const selectContinueWithWebsocketFlow = (s: RootState) => s.plan.continueWithWebsocketFlow;
export const selectReloadLeftList = (s: RootState) => s.plan.reloadLeftList;
export const selectShowCancellationDialog = (s: RootState) => s.plan.showCancellationDialog;
export const selectCancellingPlan = (s: RootState) => s.plan.cancellingPlan;
export const selectLoadingMessage = (s: RootState) => s.plan.loadingMessage;
export const selectPlanStatus = (s: RootState) => s.plan.planData?.plan?.overall_status ?? null;
export const selectPlanApproved = (s: RootState) => s.plan.planApproved;

/* ── Memoized Derived Selectors (createSelector) ─────────────────── */

/** Is the plan currently active (not completed / failed / canceled)? */
export const selectIsPlanActive = createSelector(
    selectPlanStatus,
    (status): boolean =>
        status !== null &&
        status !== PlanStatus.COMPLETED &&
        status !== PlanStatus.FAILED &&
        status !== PlanStatus.CANCELED,
);

/** Plan team (memoized — avoids new reference on unrelated planData changes) */
export const selectPlanTeam = createSelector(
    selectPlanData,
    (planData) => planData?.team ?? null,
);

/** Plan ID extracted from planData (avoids drilling into nested object each render) */
export const selectPlanId = createSelector(
    selectPlanData,
    (planData) => planData?.plan?.id ?? null,
);

/** mplan from planData (avoids new object reference when planData changes) */
export const selectMPlan = createSelector(
    selectPlanData,
    (planData) => planData?.mplan ?? null,
);

export default planSlice.reducer;
