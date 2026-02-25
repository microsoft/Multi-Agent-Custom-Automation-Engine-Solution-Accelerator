/**
 * Redux Store exports
 * 
 * This module provides centralized state management using Redux Toolkit.
 * Import the hooks and selectors from this file throughout the application.
 */

// Store
export { store, type RootState, type AppDispatch } from './store';

// Typed hooks - use these instead of plain useDispatch/useSelector
export { useAppDispatch, useAppSelector } from './hooks';

// App slice
export {
    setConfigLoaded,
    setUserInfoLoaded,
    setDarkMode,
    setWsConnected,
    setLoadingMessage,
    setIsLoading,
    setErrorMessage,
    rotateLoadingMessage,
    resetAppState,
} from './slices/appSlice';

// Chat slice
export {
    setInput,
    setSubmittingChatDisableInput,
    setAgentMessages,
    addAgentMessage,
    setStreamingMessages,
    addStreamingMessage,
    setStreamingMessageBuffer,
    appendToStreamingMessageBuffer,
    setShowBufferingText,
    setClarificationMessage,
    resetChatState,
    clearStreamingBuffer,
} from './slices/chatSlice';

// Plan slice
export {
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
} from './slices/planSlice';

// Team slice
export {
    setSelectedTeam,
    setTeams,
    setIsLoadingTeam,
    setTeamError,
    setRequiresTeamUpload,
    resetTeamState,
    initializeTeam,
    fetchUserTeams,
} from './slices/teamSlice';

// Chat History slice
export {
    setReloadLeftList,
    triggerReloadLeftList,
    clearReloadLeftList,
    setTaskHistory,
    addTaskToHistory,
    updateTaskInHistory,
    removeTaskFromHistory,
    setSelectedTaskId,
    setIsLoadingHistory,
    resetChatHistoryState,
} from './slices/chatHistorySlice';

// Citation slice
export {
    setCitations,
    addCitation,
    removeCitation,
    setActiveCitation,
    openCitationPanel,
    closeCitationPanel,
    toggleCitationPanel,
    setIsLoading as setCitationLoading,
    resetCitationState,
    selectCitation,
} from './slices/citationSlice';

// Types
export type { AppState } from './slices/appSlice';
export type { ChatState } from './slices/chatSlice';
export type { PlanState } from './slices/planSlice';
export type { TeamState } from './slices/teamSlice';
export type { ChatHistoryState, TaskHistoryItem } from './slices/chatHistorySlice';
export type { CitationState, Citation } from './slices/citationSlice';

// Granular selectors — one field per selector for minimal re-renders
export {
    // App
    selectIsConfigLoaded,
    selectIsUserInfoLoaded,
    selectIsDarkMode,
    selectWsConnected,
    selectLoadingMessage,
    selectIsLoading,
    selectErrorMessage,
    // Chat
    selectInput,
    selectSubmittingChatDisableInput,
    selectAgentMessages,
    selectStreamingMessages,
    selectStreamingMessageBuffer,
    selectShowBufferingText,
    selectClarificationMessage,
    // Plan
    selectPlanId,
    selectPlanData,
    selectPlanApprovalRequest,
    selectPlanLoading,
    selectPlanErrorLoading,
    selectWaitingForPlan,
    selectShowProcessingPlanSpinner,
    selectShowApprovalButtons,
    selectProcessingApproval,
    selectContinueWithWebsocketFlow,
    selectShowCancellationDialog,
    selectCancellingPlan,
    // Team
    selectSelectedTeam,
    selectTeams,
    selectIsLoadingTeam,
    selectTeamError,
    selectRequiresTeamUpload,
    // Chat History
    selectReloadLeftList,
    selectTaskHistory,
    selectSelectedTaskId,
    selectIsLoadingHistory,
    // Citation
    selectCitations,
    selectActiveCitation,
    selectIsCitationPanelOpen,
    selectIsCitationLoading,
} from './selectors';

// Cross-slice thunks
export { resetPlanSession } from './thunks';
