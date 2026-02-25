import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { ProcessedPlanData, MPlanData, PlanStatus } from '../../models';

/**
 * Plan slice - handles plan-specific state
 */
export interface PlanState {
    /** Current plan ID */
    planId: string | null;
    /** Processed plan data */
    planData: ProcessedPlanData | null;
    /** Plan approval request data */
    planApprovalRequest: MPlanData | null;
    /** Whether page is initially loading */
    loading: boolean;
    /** Whether there was an error loading the plan */
    errorLoading: boolean;
    /** Whether waiting for plan from server */
    waitingForPlan: boolean;
    /** Whether to show processing spinner */
    showProcessingPlanSpinner: boolean;
    /** Whether to show approval buttons */
    showApprovalButtons: boolean;
    /** Whether approval is being processed */
    processingApproval: boolean;
    /** Whether to continue with websocket flow */
    continueWithWebsocketFlow: boolean;
    /** Whether cancellation dialog is shown */
    showCancellationDialog: boolean;
    /** Whether plan is being cancelled */
    cancellingPlan: boolean;
}

const initialState: PlanState = {
    planId: null,
    planData: null,
    planApprovalRequest: null,
    loading: true,
    errorLoading: false,
    waitingForPlan: true,
    showProcessingPlanSpinner: false,
    showApprovalButtons: true,
    processingApproval: false,
    continueWithWebsocketFlow: false,
    showCancellationDialog: false,
    cancellingPlan: false,
};

const planSlice = createSlice({
    name: 'plan',
    initialState,
    reducers: {
        setPlanId: (state, action: PayloadAction<string | null>) => {
            state.planId = action.payload;
        },
        setPlanData: (state, action: PayloadAction<ProcessedPlanData | null>) => {
            state.planData = action.payload;
        },
        updatePlanStatus: (state, action: PayloadAction<PlanStatus>) => {
            if (state.planData?.plan) {
                state.planData.plan.overall_status = action.payload;
            }
        },
        setPlanApprovalRequest: (state, action: PayloadAction<MPlanData | null>) => {
            state.planApprovalRequest = action.payload;
        },
        setLoading: (state, action: PayloadAction<boolean>) => {
            state.loading = action.payload;
        },
        setErrorLoading: (state, action: PayloadAction<boolean>) => {
            state.errorLoading = action.payload;
        },
        setWaitingForPlan: (state, action: PayloadAction<boolean>) => {
            state.waitingForPlan = action.payload;
        },
        setShowProcessingPlanSpinner: (state, action: PayloadAction<boolean>) => {
            state.showProcessingPlanSpinner = action.payload;
        },
        setShowApprovalButtons: (state, action: PayloadAction<boolean>) => {
            state.showApprovalButtons = action.payload;
        },
        setProcessingApproval: (state, action: PayloadAction<boolean>) => {
            state.processingApproval = action.payload;
        },
        setContinueWithWebsocketFlow: (state, action: PayloadAction<boolean>) => {
            state.continueWithWebsocketFlow = action.payload;
        },
        setShowCancellationDialog: (state, action: PayloadAction<boolean>) => {
            state.showCancellationDialog = action.payload;
        },
        setCancellingPlan: (state, action: PayloadAction<boolean>) => {
            state.cancellingPlan = action.payload;
        },
        /**
         * Reset plan state to initial values
         */
        resetPlanState: () => initialState,
        /**
         * Reset plan variables for loading a new plan
         */
        resetPlanVariables: (state) => {
            state.planData = null;
            state.planApprovalRequest = null;
            state.loading = true;
            state.errorLoading = false;
            state.waitingForPlan = true;
            state.showProcessingPlanSpinner = false;
            state.showApprovalButtons = true;
            state.processingApproval = false;
            state.continueWithWebsocketFlow = false;
        },
        /**
         * Handle plan received from websocket
         */
        handlePlanReceived: (state, action: PayloadAction<MPlanData>) => {
            state.planApprovalRequest = action.payload;
            state.waitingForPlan = false;
            state.showProcessingPlanSpinner = false;
        },
        /**
         * Handle plan approval started
         */
        handleApprovalStarted: (state) => {
            state.processingApproval = true;
        },
        /**
         * Handle plan approval completed
         */
        handleApprovalCompleted: (state) => {
            state.processingApproval = false;
            state.showProcessingPlanSpinner = true;
            state.showApprovalButtons = false;
        },
    },
});

export const {
    setPlanId,
    setPlanData,
    updatePlanStatus,
    setPlanApprovalRequest,
    setLoading,
    setErrorLoading,
    setWaitingForPlan,
    setShowProcessingPlanSpinner,
    setShowApprovalButtons,
    setProcessingApproval,
    setContinueWithWebsocketFlow,
    setShowCancellationDialog,
    setCancellingPlan,
    resetPlanState,
    resetPlanVariables,
    handlePlanReceived,
    handleApprovalStarted,
    handleApprovalCompleted,
} = planSlice.actions;

export default planSlice.reducer;
