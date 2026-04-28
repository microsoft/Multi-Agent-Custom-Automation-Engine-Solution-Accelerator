import React, { useCallback, useEffect} from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Spinner, Text } from '@fluentui/react-components';

/* ── Services / API ──────────────────────────────────────────── */
import { APIService } from '../api/apiService';
import { PlanDataService } from '../store/PlanDataService';
import webSocketService from '../store/WebSocketService';

/* ── Models ──────────────────────────────────────────────────── */
import {
    AgentMessageData,
    AgentMessageType,
} from '../models';

/* ── Redux ───────────────────────────────────────────────────── */
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
    selectPlanData,
    selectPlanLoading,
    selectErrorLoading,
    selectPlanApprovalRequest,
    selectProcessingApproval,
    selectShowApprovalButtons,
    selectShowProcessingPlanSpinner,
    selectShowCancellationDialog,
    selectCancellingPlan,
    selectLoadingMessage,
    selectReloadLeftList,
    selectWaitingForPlan,
    setReloadLeftList,
    setProcessingApproval,
    setShowProcessingPlanSpinner,
    setShowCancellationDialog,
    setCancellingPlan,
    setLoadingMessage,
    setErrorLoading,
    planApprovalAccepted,
    planApprovalRejected,
} from '../store/slices/planSlice';
import {
    selectInput,
    selectSubmittingChatDisable,
    selectClarificationMessage,
    selectAgentMessages,
    setInput,
    setSubmittingChatDisableInput,
    addAgentMessage,
} from '../store/slices/chatSlice';
import {
    selectStreamingMessages,
    selectStreamingMessageBuffer,
    selectShowBufferingText,
} from '../store/slices/streamingSlice';
import { selectWsConnected } from '../store/slices/appSlice';
import { selectSelectedTeam } from '../store/slices/teamSlice';

/* ── Custom Hooks ────────────────────────────────────────────── */
import { usePlanWebSocket } from '../hooks/usePlanWebSocket';
import { usePlanActions } from '../hooks/usePlanActions';
import { useAutoScroll } from '../hooks/useAutoScroll';
import { usePlanCancellationAlert } from '../hooks/usePlanCancellationAlert';

/* ── Components ──────────────────────────────────────────────── */
import PlanChat from '../components/content/PlanChat';
import PlanPanelRight from '../components/content/PlanPanelRight';
import PlanPanelLeft from '../components/content/PlanPanelLeft';
import CoralShellColumn from '../commonComponents/components/Layout/CoralShellColumn';
import CoralShellRow from '../commonComponents/components/Layout/CoralShellRow';
import Content from '../commonComponents/components/Content/Content';
import ContentToolbar from '../commonComponents/components/Content/ContentToolbar';
import { useInlineToaster } from '../components/toast/InlineToaster';
import Octo from '../commonComponents/imports/Octopus.png';
import LoadingMessage, { loadingMessages } from '../commonComponents/components/LoadingMessage';
import PlanCancellationDialog from '../components/common/PlanCancellationDialog';
import '../styles/PlanPage.css';

// Singleton API service
const apiService = new APIService();

const getPlanProcessingStatusMessage = (elapsedSeconds: number): string => {
    if (elapsedSeconds < 10) {
        return 'Analyzing creative brief...';
    }

    if (elapsedSeconds < 25) {
        return 'Generating marketing copy...';
    }

    if (elapsedSeconds < 35) {
        return 'Creating image prompt...';
    }

    if (elapsedSeconds < 55) {
        return 'Generating image with AI...';
    }

    if (elapsedSeconds < 70) {
        return 'Running compliance check...';
    }

    return 'Finalizing content...';
};

/* ================================================================
 *  PlanPage — refactored to use Redux + extracted hooks
 * ================================================================ */
const PlanPage: React.FC = () => {
    const { planId } = useParams<{ planId: string }>();
    const navigate = useNavigate();
    const dispatch = useAppDispatch();
    const { showToast, dismissToast } = useInlineToaster();
    const { messagesContainerRef, scrollToBottom } = useAutoScroll();
    const { loadPlanData, resetPlanVariables } = usePlanActions();

    /* ── Redux Selectors (granular — Point 10) ──────────────── */
    const planData = useAppSelector(selectPlanData);
    const loading = useAppSelector(selectPlanLoading);
    const errorLoading = useAppSelector(selectErrorLoading);
    const planApprovalRequest = useAppSelector(selectPlanApprovalRequest);
    const processingApproval = useAppSelector(selectProcessingApproval);
    const showApprovalButtons = useAppSelector(selectShowApprovalButtons);
    const showProcessingPlanSpinner = useAppSelector(selectShowProcessingPlanSpinner);
    const showCancellationDialog = useAppSelector(selectShowCancellationDialog);
    const cancellingPlan = useAppSelector(selectCancellingPlan);
    const loadingMessage = useAppSelector(selectLoadingMessage);
    const reloadLeftList = useAppSelector(selectReloadLeftList);
    const waitingForPlan = useAppSelector(selectWaitingForPlan);
    const input = useAppSelector(selectInput);
    const submittingChatDisableInput = useAppSelector(selectSubmittingChatDisable);
    const clarificationMessage = useAppSelector(selectClarificationMessage);
    const agentMessages = useAppSelector(selectAgentMessages);
    const streamingMessages = useAppSelector(selectStreamingMessages);
    const streamingMessageBuffer = useAppSelector(selectStreamingMessageBuffer);
    const showBufferingText = useAppSelector(selectShowBufferingText);
    const wsConnected = useAppSelector(selectWsConnected);
    const selectedTeam = useAppSelector(selectSelectedTeam);

    /* ── Cancellation alert hook ────────────────────────────── */
    const [pendingNavigation, setPendingNavigation] = React.useState<(() => void) | null>(null);
    const [processingElapsedSeconds, setProcessingElapsedSeconds] = React.useState<number>(0);
    const processingStatusMessage = getPlanProcessingStatusMessage(processingElapsedSeconds);

    const { isPlanActive } = usePlanCancellationAlert({
        planData,
        planApprovalRequest,
        onNavigate: pendingNavigation || (() => {}),
    });

    /* ── Memoized formatErrorMessage ────────────────────────── */
    const formatErrorMessage = useCallback((content: string): string => {
        const lines = content.split('\n');
        return lines
            .map((line, idx) => {
                if (idx === 0) return `\u26A0\uFE0F ${line}`;
                if (line.trim() === '') return '';
                return `&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;${line}`;
            })
            .join('\n');
    }, []);

    /* ── WebSocket subscriptions (extracted hook) ───────────── */
    usePlanWebSocket({ planId, scrollToBottom, formatErrorMessage, showToast });

    /* ── Navigation with cancellation check ─────────────────── */
    const handleNavigationWithAlert = useCallback(
        (navigationFn: () => void) => {
            if (!isPlanActive()) {
                navigationFn();
                return;
            }
            setPendingNavigation(() => navigationFn);
            dispatch(setShowCancellationDialog(true));
        },
        [isPlanActive, dispatch],
    );

    const handleConfirmCancellation = useCallback(async () => {
        dispatch(setCancellingPlan(true));
        try {
            if (planApprovalRequest?.id) {
                await apiService.approvePlan({
                    m_plan_id: planApprovalRequest.id,
                    plan_id: planData?.plan?.id ?? '',
                    approved: false,
                    feedback: 'Plan cancelled by user navigation',
                });
            }
            pendingNavigation?.();
            webSocketService.disconnect();
        } catch {
            showToast('Failed to cancel the plan properly, but navigation will continue.', 'error');
            pendingNavigation?.();
        } finally {
            dispatch(setCancellingPlan(false));
            dispatch(setShowCancellationDialog(false));
            setPendingNavigation(null);
        }
    }, [planApprovalRequest, planData, pendingNavigation, showToast, dispatch]);

    const handleCancelDialog = useCallback(() => {
        dispatch(setShowCancellationDialog(false));
        setPendingNavigation(null);
    }, [dispatch]);

    /* ── Plan Approval / Rejection ──────────────────────────── */
    const handleApprovePlan = useCallback(async () => {
        if (!planApprovalRequest) return;
        dispatch(setProcessingApproval(true));
        const id = showToast('Submitting Approval', 'progress');
        try {
            await apiService.approvePlan({
                m_plan_id: planApprovalRequest.id,
                plan_id: planData?.plan?.id ?? '',
                approved: true,
                feedback: 'Plan approved by user',
            });
            dismissToast(id);
            /* P0: single compound action replaces 3 separate dispatches */
            dispatch(planApprovalAccepted());
        } catch {
            dismissToast(id);
            showToast('Failed to submit approval', 'error');
        } finally {
            dispatch(setProcessingApproval(false));
        }
    }, [planApprovalRequest, planData, showToast, dismissToast, dispatch]);

    const handleRejectPlan = useCallback(async () => {
        if (!planApprovalRequest) return;
        dispatch(setProcessingApproval(true));
        const id = showToast('Submitting cancellation', 'progress');
        try {
            await apiService.approvePlan({
                m_plan_id: planApprovalRequest.id,
                plan_id: planData?.plan?.id ?? '',
                approved: false,
                feedback: 'Plan rejected by user',
            });
            dismissToast(id);
            navigate('/');
        } catch {
            dismissToast(id);
            showToast('Failed to submit cancellation', 'error');
            navigate('/');
        } finally {
            /* P0: single compound action replaces multiple state resets */
            dispatch(planApprovalRejected());
        }
    }, [planApprovalRequest, planData, navigate, showToast, dismissToast, dispatch]);

    /* ── Chat submission ────────────────────────────────────── */
    const handleOnchatSubmit = useCallback(
        async (chatInput: string) => {
            if (!chatInput.trim()) {
                showToast('Please enter a clarification', 'error');
                return;
            }
            dispatch(setInput(''));
            if (!planData?.plan) return;
            dispatch(setSubmittingChatDisableInput(true));
            const id = showToast('Submitting clarification', 'progress');
            try {
                await PlanDataService.submitClarification({
                    request_id: clarificationMessage?.request_id || '',
                    answer: chatInput,
                    plan_id: planData.plan.id,
                    m_plan_id: planApprovalRequest?.id || '',
                });
                dispatch(setInput(''));
                dismissToast(id);
                showToast('Clarification submitted successfully', 'success');
                const agentMessageData: AgentMessageData = {
                    agent: 'human',
                    agent_type: AgentMessageType.HUMAN_AGENT,
                    timestamp: Date.now(),
                    steps: [],
                    next_steps: [],
                    content: chatInput,
                    raw_data: chatInput,
                };
                dispatch(addAgentMessage(agentMessageData));
                dispatch(setSubmittingChatDisableInput(true));
                dispatch(setShowProcessingPlanSpinner(true));
                scrollToBottom();
            } catch {
                dispatch(setShowProcessingPlanSpinner(false));
                dismissToast(id);
                dispatch(setSubmittingChatDisableInput(false));
                showToast('Failed to submit clarification', 'error');
            }
        },
        [planData, clarificationMessage, planApprovalRequest, showToast, dismissToast, dispatch, scrollToBottom],
    );

    /* ── Left-panel handlers ────────────────────────────────── */
    const handleNewTaskButton = useCallback(() => {
        handleNavigationWithAlert(() => navigate('/', { state: { focusInput: true } }));
    }, [navigate, handleNavigationWithAlert]);

    const resetReload = useCallback(() => {
        dispatch(setReloadLeftList(false));
    }, [dispatch]);

    /* ── Loading message rotation ───────────────────────────── */
    useEffect(() => {
        if (!loading) return;
        let index = 0;
        dispatch(setLoadingMessage(loadingMessages[0]));
        const interval = setInterval(() => {
            index = (index + 1) % loadingMessages.length;
            dispatch(setLoadingMessage(loadingMessages[index]));
        }, 3000);
        return () => clearInterval(interval);
    }, [loading, dispatch]);

    /* ── Plan execution elapsed timer ───────────────────────── */
    useEffect(() => {
        if (!showProcessingPlanSpinner) {
            setProcessingElapsedSeconds(0);
            return;
        }

        setProcessingElapsedSeconds(0);
        const interval = setInterval(() => {
            setProcessingElapsedSeconds((currentSeconds: number) => currentSeconds + 1);
        }, 1000);

        return () => clearInterval(interval);
    }, [showProcessingPlanSpinner]);

    /* ── Initial plan load ──────────────────────────────────── */
    useEffect(() => {
        if (!planId) {
            resetPlanVariables();
            dispatch(setErrorLoading(true));
            return;
        }
        loadPlanData(planId, false);
    }, [planId, loadPlanData, resetPlanVariables, dispatch]);

    /* ── Render: Error state ────────────────────────────────── */
    if (errorLoading) {
        return (
            <CoralShellColumn>
                <CoralShellRow>
                    <PlanPanelLeft
                        reloadTasks={reloadLeftList}
                        onNewTaskButton={handleNewTaskButton}
                        restReload={resetReload}
                        onTeamSelect={() => {}}
                        onTeamUpload={async () => {}}
                        isHomePage={false}
                        selectedTeam={selectedTeam}
                        onNavigationWithAlert={handleNavigationWithAlert}
                    />
                    <Content>
                        <div className="plan-error-message">
                            <Text size={500}>An error occurred while loading the plan</Text>
                        </div>
                    </Content>
                </CoralShellRow>
            </CoralShellColumn>
        );
    }

    /* ── Render: Normal state ───────────────────────────────── */
    return (
        <CoralShellColumn>
            <CoralShellRow>
                <PlanPanelLeft
                    reloadTasks={reloadLeftList}
                    onNewTaskButton={handleNewTaskButton}
                    restReload={resetReload}
                    onTeamSelect={() => {}}
                    onTeamUpload={async () => {}}
                    isHomePage={false}
                    selectedTeam={selectedTeam}
                    onNavigationWithAlert={handleNavigationWithAlert}
                />

                <Content>
                    {loading || !planData ? (
                        <>
                            <div className="plan-loading-spinner">
                                <Spinner size="medium" />
                                <Text>Loading plan data...</Text>
                            </div>
                            <LoadingMessage loadingMessage={loadingMessage} iconSrc={Octo} />
                        </>
                    ) : (
                        <>
                            <ContentToolbar panelTitle="Multi-Agent Planner" />
                            <PlanChat
                                planData={planData}
                                OnChatSubmit={handleOnchatSubmit}
                                loading={loading}
                                setInput={(val: string) => dispatch(setInput(val))}
                                submittingChatDisableInput={submittingChatDisableInput}
                                input={input}
                                streamingMessages={streamingMessages}
                                wsConnected={wsConnected}
                                planApprovalRequest={planApprovalRequest}
                                waitingForPlan={waitingForPlan}
                                messagesContainerRef={messagesContainerRef}
                                streamingMessageBuffer={streamingMessageBuffer}
                                showBufferingText={showBufferingText}
                                agentMessages={agentMessages}
                                showProcessingPlanSpinner={showProcessingPlanSpinner}
                                processingElapsedSeconds={processingElapsedSeconds}
                                processingStatusMessage={processingStatusMessage}
                                showApprovalButtons={showApprovalButtons}
                                processingApproval={processingApproval}
                                handleApprovePlan={handleApprovePlan}
                                handleRejectPlan={handleRejectPlan}
                            />
                        </>
                    )}
                </Content>

                <PlanPanelRight
                    planData={planData}
                    loading={loading}
                    planApprovalRequest={planApprovalRequest}
                />
            </CoralShellRow>

            <PlanCancellationDialog
                isOpen={showCancellationDialog}
                onConfirm={handleConfirmCancellation}
                onCancel={handleCancelDialog}
                loading={cancellingPlan}
            />
        </CoralShellColumn>
    );
};

const MemoizedPlanPage = React.memo(PlanPage);
MemoizedPlanPage.displayName = 'PlanPage';
export default MemoizedPlanPage;
