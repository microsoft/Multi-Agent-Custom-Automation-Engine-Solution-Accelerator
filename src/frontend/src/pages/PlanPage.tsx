import React, { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Spinner, Text } from "@fluentui/react-components";
import PlanChat from "../components/content/PlanChat";
import PlanPanelRight from "../components/content/PlanPanelRight";
import PlanPanelLeft from "../components/content/PlanPanelLeft";
import CoralShellColumn from "../coral/components/Layout/CoralShellColumn";
import CoralShellRow from "../coral/components/Layout/CoralShellRow";
import Content from "../coral/components/Content/Content";
import ContentToolbar from "../coral/components/Content/ContentToolbar";
import {
    useInlineToaster,
} from "../components/toast/InlineToaster";
import Octo from "../coral/imports/Octopus.png";
import LoadingMessage, { loadingMessages } from "../coral/components/LoadingMessage";
import webSocketService from "../services/WebSocketService";
import { apiService } from "../api/apiService";
import { usePlanCancellationAlert } from "../hooks/usePlanCancellationAlert";
import PlanCancellationDialog from "../components/common/PlanCancellationDialog";
import { usePlanLoader } from "../hooks/usePlanLoader";
import { usePlanWebSocket } from "../hooks/usePlanWebSocket";
import { usePlanApproval } from "../hooks/usePlanApproval";
import { usePlanChat } from "../hooks/usePlanChat";
import { useAutoScroll } from "../hooks/useAutoScroll";
import { useLoadingMessages } from "../hooks/useLoadingMessages";
import {
    useAppDispatch,
    useAppSelector,
    selectPlanData,
    selectPlanLoading,
    selectPlanErrorLoading,
    selectReloadLeftList,
    selectSelectedTeam,
    selectWsConnected,
    selectStreamingMessages,
    selectStreamingMessageBuffer,
    selectShowBufferingText,
    selectAgentMessages,
    selectShowProcessingPlanSpinner,
    selectShowApprovalButtons,
    selectProcessingApproval,
    selectPlanApprovalRequest,
    selectWaitingForPlan,
    selectShowCancellationDialog,
    selectCancellingPlan,
    setCancellingPlan,
    setShowCancellationDialog,
    setSelectedTeam,
    clearReloadLeftList,
} from "../store";
import "../styles/PlanPage.css"

/**
 * Page component for displaying a specific plan
 * Accessible via the route /plan/{plan_id}
 *
 * All plan/chat/team state is read from Redux via granular selectors.
 * Only `pendingNavigation` stays as local useState (non-serializable function ref).
 */
const PlanPage: React.FC = () => {
    const { planId } = useParams<{ planId: string }>();
    const navigate = useNavigate();
    const dispatch = useAppDispatch();
    const { showToast, dismissToast } = useInlineToaster();

    // ── Redux selectors (replaces 15 useState calls) ──
    const planData = useAppSelector(selectPlanData);
    const loading = useAppSelector(selectPlanLoading);
    const errorLoading = useAppSelector(selectPlanErrorLoading);
    const reloadLeftList = useAppSelector(selectReloadLeftList);
    const selectedTeam = useAppSelector(selectSelectedTeam);
    const wsConnected = useAppSelector(selectWsConnected);
    const streamingMessages = useAppSelector(selectStreamingMessages);
    const streamingMessageBuffer = useAppSelector(selectStreamingMessageBuffer);
    const showBufferingText = useAppSelector(selectShowBufferingText);
    const agentMessages = useAppSelector(selectAgentMessages);
    const showProcessingPlanSpinner = useAppSelector(selectShowProcessingPlanSpinner);
    const showApprovalButtons = useAppSelector(selectShowApprovalButtons);
    const processingApproval = useAppSelector(selectProcessingApproval);
    const planApprovalRequest = useAppSelector(selectPlanApprovalRequest);
    const waitingForPlan = useAppSelector(selectWaitingForPlan);
    const showCancellationDialog = useAppSelector(selectShowCancellationDialog);
    const cancellingPlan = useAppSelector(selectCancellingPlan);

    // ── Non-serializable local state (function ref — cannot go in Redux) ──
    const [pendingNavigation, setPendingNavigation] = useState<(() => void) | null>(null);

    // ── Auto-scroll hook ──
    const { containerRef: messagesContainerRef, scrollToBottom } = useAutoScroll();

    // ── Loading message rotation ──
    const loadingMessage = useLoadingMessages(loadingMessages, true);

    // ── Hooks (all use Redux internally — no callback interfaces) ──
    usePlanLoader(planId);

    const {
        handleApprovePlan,
        handleRejectPlan,
    } = usePlanApproval(
        showToast,
        dismissToast,
        (path: string) => navigate(path),
    );

    const {
        input,
        setInputValue,
        submittingChatDisableInput,
        handleOnchatSubmit,
    } = usePlanChat(
        showToast,
        dismissToast,
        scrollToBottom
    );

    usePlanWebSocket(planId, {
        scrollToBottom,
        showToast,
    });

    // ── Plan cancellation alert ──
    const { isPlanActive } = usePlanCancellationAlert({
        onNavigate: pendingNavigation || (() => { })
    });

    const handleNavigationWithAlert = useCallback((navigationFn: () => void) => {
        if (!isPlanActive()) {
            navigationFn();
            return;
        }
        setPendingNavigation(() => navigationFn);
        dispatch(setShowCancellationDialog(true));
    }, [isPlanActive, dispatch]);

    const handleConfirmCancellation = useCallback(async () => {
        dispatch(setCancellingPlan(true));
        try {
            if (planApprovalRequest?.id) {
                await apiService.approvePlan({
                    m_plan_id: planApprovalRequest.id,
                    plan_id: planData?.plan?.id || "",
                    approved: false,
                    feedback: 'Plan cancelled by user navigation'
                });
            }
            if (pendingNavigation) pendingNavigation();
            webSocketService.disconnect();
        } catch (error) {
            showToast('Failed to cancel the plan properly, but navigation will continue.', 'error');
            if (pendingNavigation) pendingNavigation();
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

    // ── Sync selected team from plan data ──
    useEffect(() => {
        if (planData?.team) {
            dispatch(setSelectedTeam(planData.team));
        }
    }, [planData, dispatch]);

    // ── Navigation helpers ──
    const handleNewTaskButton = useCallback(() => {
        handleNavigationWithAlert(() => {
            navigate("/", { state: { focusInput: true } });
        });
    }, [navigate, handleNavigationWithAlert]);

    const resetReload = useCallback(() => {
        dispatch(clearReloadLeftList());
    }, [dispatch]);

    // ── Render ──
    if (errorLoading) {
        return (
            <CoralShellColumn>
                <CoralShellRow>
                    <PlanPanelLeft
                        reloadTasks={reloadLeftList}
                        onNewTaskButton={handleNewTaskButton}
                        restReload={resetReload}
                        onTeamSelect={() => { }}
                        onTeamUpload={async () => { }}
                        isHomePage={false}
                        selectedTeam={selectedTeam}
                        onNavigationWithAlert={handleNavigationWithAlert}
                    />
                    <Content>
                        <div className="plan-error-message">
                            <Text size={500}>
                                {"An error occurred while loading the plan"}
                            </Text>
                        </div>
                    </Content>
                </CoralShellRow>
            </CoralShellColumn>
        );
    }

    return (
        <CoralShellColumn>
            <CoralShellRow>
                <PlanPanelLeft
                    reloadTasks={reloadLeftList}
                    onNewTaskButton={handleNewTaskButton}
                    restReload={resetReload}
                    onTeamSelect={() => { }}
                    onTeamUpload={async () => { }}
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
                            <LoadingMessage
                                loadingMessage={loadingMessage}
                                iconSrc={Octo}
                            />
                        </>
                    ) : (
                        <>
                            <ContentToolbar
                                panelTitle="Multi-Agent Planner"
                            />
                            
                            <PlanChat
                                planData={planData}
                                OnChatSubmit={handleOnchatSubmit}
                                loading={loading}
                                setInput={setInputValue}
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
                                showApprovalButtons={showApprovalButtons}
                                processingApproval={processingApproval}
                                handleApprovePlan={handleApprovePlan}
                                handleRejectPlan={handleRejectPlan}
                            />
                        </>
                    )}
                </Content>

                <PlanPanelRight
                    planData={planData!}
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

export default PlanPage;