/**
 * Granular Redux Selectors
 *
 * Each selector targets a single field so that components only
 * re-render when the specific slice of state they depend on changes.
 *
 * Usage:
 *   const wsConnected = useAppSelector(selectWsConnected);
 *
 * Never destructure the entire slice:
 *   ❌  const { wsConnected, isDarkMode } = useAppSelector(state => state.app);
 *   ✅  const wsConnected = useAppSelector(selectWsConnected);
 *   ✅  const isDarkMode  = useAppSelector(selectIsDarkMode);
 */
import type { RootState } from './store';

// ── App Selectors ────────────────────────────────────────────────────────────

export const selectIsConfigLoaded = (state: RootState) => state.app.isConfigLoaded;
export const selectIsUserInfoLoaded = (state: RootState) => state.app.isUserInfoLoaded;
export const selectIsDarkMode = (state: RootState) => state.app.isDarkMode;
export const selectWsConnected = (state: RootState) => state.app.wsConnected;
export const selectLoadingMessage = (state: RootState) => state.app.loadingMessage;
export const selectIsLoading = (state: RootState) => state.app.isLoading;
export const selectErrorMessage = (state: RootState) => state.app.errorMessage;

// ── Chat Selectors ───────────────────────────────────────────────────────────

export const selectInput = (state: RootState) => state.chat.input;
export const selectSubmittingChatDisableInput = (state: RootState) => state.chat.submittingChatDisableInput;
export const selectAgentMessages = (state: RootState) => state.chat.agentMessages;
export const selectStreamingMessages = (state: RootState) => state.chat.streamingMessages;
export const selectStreamingMessageBuffer = (state: RootState) => state.chat.streamingMessageBuffer;
export const selectShowBufferingText = (state: RootState) => state.chat.showBufferingText;
export const selectClarificationMessage = (state: RootState) => state.chat.clarificationMessage;

// ── Plan Selectors ───────────────────────────────────────────────────────────

export const selectPlanId = (state: RootState) => state.plan.planId;
export const selectPlanData = (state: RootState) => state.plan.planData;
export const selectPlanApprovalRequest = (state: RootState) => state.plan.planApprovalRequest;
export const selectPlanLoading = (state: RootState) => state.plan.loading;
export const selectPlanErrorLoading = (state: RootState) => state.plan.errorLoading;
export const selectWaitingForPlan = (state: RootState) => state.plan.waitingForPlan;
export const selectShowProcessingPlanSpinner = (state: RootState) => state.plan.showProcessingPlanSpinner;
export const selectShowApprovalButtons = (state: RootState) => state.plan.showApprovalButtons;
export const selectProcessingApproval = (state: RootState) => state.plan.processingApproval;
export const selectContinueWithWebsocketFlow = (state: RootState) => state.plan.continueWithWebsocketFlow;
export const selectShowCancellationDialog = (state: RootState) => state.plan.showCancellationDialog;
export const selectCancellingPlan = (state: RootState) => state.plan.cancellingPlan;

// ── Team Selectors ───────────────────────────────────────────────────────────

export const selectSelectedTeam = (state: RootState) => state.team.selectedTeam;
export const selectTeams = (state: RootState) => state.team.teams;
export const selectIsLoadingTeam = (state: RootState) => state.team.isLoadingTeam;
export const selectTeamError = (state: RootState) => state.team.teamError;
export const selectRequiresTeamUpload = (state: RootState) => state.team.requiresTeamUpload;

// ── Chat History Selectors ───────────────────────────────────────────────────

export const selectReloadLeftList = (state: RootState) => state.chatHistory.reloadLeftList;
export const selectTaskHistory = (state: RootState) => state.chatHistory.taskHistory;
export const selectSelectedTaskId = (state: RootState) => state.chatHistory.selectedTaskId;
export const selectIsLoadingHistory = (state: RootState) => state.chatHistory.isLoadingHistory;

// ── Citation Selectors ───────────────────────────────────────────────────────

export const selectCitations = (state: RootState) => state.citation.citations;
export const selectActiveCitation = (state: RootState) => state.citation.activeCitation;
export const selectIsCitationPanelOpen = (state: RootState) => state.citation.isPanelOpen;
export const selectIsCitationLoading = (state: RootState) => state.citation.isLoading;
