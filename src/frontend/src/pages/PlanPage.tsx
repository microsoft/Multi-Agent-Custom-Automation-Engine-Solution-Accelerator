import React, { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Spinner, Text } from "@fluentui/react-components";
import { PlanDataService } from "../services/PlanDataService";
import { ProcessedPlanData, WebsocketMessageType, MPlanData, AgentMessageData, AgentMessageType, ParsedUserClarification, AgentType, PlanStatus, FinalMessage, TeamConfig } from "../models";
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
import PanelRightToggles from "../coral/components/Header/PanelRightToggles";
import { TaskListSquareLtr } from "../coral/imports/bundleicons";
import LoadingMessage, { loadingMessages } from "../coral/components/LoadingMessage";
import webSocketService from "../services/WebSocketService";
import { APIService } from "../api/apiService";
import { StreamMessage, StreamingPlanUpdate } from "../models";
import { usePlanCancellationAlert } from "../hooks/usePlanCancellationAlert";
import PlanCancellationDialog from "../components/common/PlanCancellationDialog";
import "../styles/PlanPage.css"

// Create API service instance
const apiService = new APIService();

/**
 * Page component for displaying a specific plan
 * Accessible via the route /plan/{plan_id}
 */
const PlanPage: React.FC = () => {
    const { planId } = useParams<{ planId: string }>();
    const navigate = useNavigate();
    const { showToast, dismissToast } = useInlineToaster();
    const messagesContainerRef = useRef<HTMLDivElement>(null);
    const [input, setInput] = useState<string>("");
    const [planData, setPlanData] = useState<ProcessedPlanData | any>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [submittingChatDisableInput, setSubmittingChatDisableInput] = useState<boolean>(true);
    const [errorLoading, setErrorLoading] = useState<boolean>(false);
    const [clarificationMessage, setClarificationMessage] = useState<ParsedUserClarification | null>(null);
    const [processingApproval, setProcessingApproval] = useState<boolean>(false);
    const [planApprovalRequest, setPlanApprovalRequest] = useState<MPlanData | null>(null);
    const [reloadLeftList, setReloadLeftList] = useState<boolean>(true);
    const [waitingForPlan, setWaitingForPlan] = useState<boolean>(true);
    const [showProcessingPlanSpinner, setShowProcessingPlanSpinner] = useState<boolean>(false);
    const [showApprovalButtons, setShowApprovalButtons] = useState<boolean>(true);
    const [continueWithWebsocketFlow, setContinueWithWebsocketFlow] = useState<boolean>(false);
    const [selectedTeam, setSelectedTeam] = useState<TeamConfig | null>(null);
    // WebSocket connection state
    const [wsConnected, setWsConnected] = useState<boolean>(false);
    const [streamingMessages, setStreamingMessages] = useState<StreamingPlanUpdate[]>([]);
    const [streamingMessageBuffer, setStreamingMessageBuffer] = useState<string>("");
    const [showBufferingText, setShowBufferingText] = useState<boolean>(false);
    const [agentMessages, setAgentMessages] = useState<AgentMessageData[]>([]);
    const formatErrorMessage = useCallback((content: string): string => {
        // Split content by newlines and add proper indentation
        const lines = content.split('\n');
        const formattedLines = lines.map((line, index) => {
            if (index === 0) {
                return `⚠️ ${line}`;
            } else if (line.trim() === '') {
                return ''; // Preserve blank lines
            } else {
                return `&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;${line}`;
            }
        });
        return formattedLines.join('\n');
    }, []);
    // Plan approval state - track when plan is approved
    const [planApproved, setPlanApproved] = useState<boolean>(false);

    // Plan cancellation dialog state
    const [showCancellationDialog, setShowCancellationDialog] = useState<boolean>(false);
    const [pendingNavigation, setPendingNavigation] = useState<(() => void) | null>(null);
    const [cancellingPlan, setCancellingPlan] = useState<boolean>(false);

    const [loadingMessage, setLoadingMessage] = useState<string>(loadingMessages[0]);

    // Plan cancellation alert hook
    const { isPlanActive, handleNavigationWithConfirmation } = usePlanCancellationAlert({
        planData,
        planApprovalRequest,
        onNavigate: pendingNavigation || (() => {})
    });

    // Handle navigation with plan cancellation check
    const handleNavigationWithAlert = useCallback((navigationFn: () => void) => {
        if (!isPlanActive()) {
            // Plan is not active, proceed with navigation
            navigationFn();
            return;
        }

        // Plan is active, show confirmation dialog
        setPendingNavigation(() => navigationFn);
        setShowCancellationDialog(true);
    }, [isPlanActive]);

    // Handle confirmation dialog response
    const handleConfirmCancellation = useCallback(async () => {
        setCancellingPlan(true);
        
        try {
            if (planApprovalRequest?.id) {
                await apiService.approvePlan({
                    m_plan_id: planApprovalRequest.id,
                    plan_id: planData?.plan?.id,
                    approved: false,
                    feedback: 'Plan cancelled by user navigation'
                });
            }

            // Execute the pending navigation
            if (pendingNavigation) {
                pendingNavigation();
            }
        } catch (error) {
            console.error('❌ Failed to cancel plan:', error);
            showToast('Failed to cancel the plan properly, but navigation will continue.', 'error');
            // Still proceed with navigation even if cancellation failed
            if (pendingNavigation) {
                pendingNavigation();
            }
        } finally {
            setCancellingPlan(false);
            setShowCancellationDialog(false);
            setPendingNavigation(null);
        }
    }, [planApprovalRequest, planData, pendingNavigation, showToast]);

    const handleCancelDialog = useCallback(() => {
        setShowCancellationDialog(false);
        setPendingNavigation(null);
    }, []);



    const processAgentMessage = useCallback((agentMessageData: AgentMessageData, planData: ProcessedPlanData, is_final: boolean = false, streaming_message: string = '') => {

        // Persist / forward to backend (fire-and-forget with logging)
        const agentMessageResponse = PlanDataService.createAgentMessageResponse(agentMessageData, planData, is_final, streaming_message);
        console.log('📤 Persisting agent message:', agentMessageResponse);
        const sendPromise = apiService.sendAgentMessage(agentMessageResponse)
            .then(saved => {
                console.log('[agent_message][persisted]', {
                    agent: agentMessageData.agent,
                    type: agentMessageData.agent_type,
                    ts: agentMessageData.timestamp
                });
                
                // If this is a final message, refresh the task list after successful persistence
                if (is_final) {
                    // Single refresh with a delay to ensure backend processing is complete
                    setTimeout(() => {
                        setReloadLeftList(true);
                    }, 1000);
                }
            })
            .catch(err => {
                console.warn('[agent_message][persist-failed]', err);
                // Even if persistence fails, still refresh the task list for final messages
                // The local plan data has been updated, so the UI should reflect that
                if (is_final) {
                    setTimeout(() => {
                        setReloadLeftList(true);
                    }, 1000);
                }
            });

        return sendPromise;

    }, [setReloadLeftList]);

    const resetPlanVariables = useCallback(() => {
        setInput("");
        setPlanData(null);
        setLoading(true);
        setSubmittingChatDisableInput(true);
        setErrorLoading(false);
        setClarificationMessage(null);
        setProcessingApproval(false);
        setPlanApprovalRequest(null);
        setReloadLeftList(true);
        setWaitingForPlan(true);
        setShowProcessingPlanSpinner(false);
        setShowApprovalButtons(true);
        setContinueWithWebsocketFlow(false);
        setWsConnected(false);
        setStreamingMessages([]);
        setStreamingMessageBuffer("");
        setShowBufferingText(false);
        setAgentMessages([]);
    }, [
        setInput,
        setPlanData,
        setLoading,
        setSubmittingChatDisableInput,
        setErrorLoading,
        setClarificationMessage,
        setProcessingApproval,
        setPlanApprovalRequest,
        setReloadLeftList,
        setWaitingForPlan,
        setShowProcessingPlanSpinner,
        setShowApprovalButtons,
        setContinueWithWebsocketFlow,
        setWsConnected,
        setStreamingMessages,
        setStreamingMessageBuffer,
        setShowBufferingText,
        setAgentMessages
    ]);

    // Auto-scroll helper
    const scrollToBottom = useCallback(() => {
        setTimeout(() => {
            if (messagesContainerRef.current) {
                //messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
                messagesContainerRef.current?.scrollTo({
                    top: messagesContainerRef.current.scrollHeight,
                    behavior: "smooth",
                });
            }
        }, 100);
    }, []);

    const [isProcessing, setIsProcessing] = useState<boolean>(false);
    const [showProcessingMessage, setShowProcessingMessage] = useState<boolean>(false);

    //WebsocketMessageType.PLAN_APPROVAL_REQUEST
    useEffect(() => {
        const unsubscribe = webSocketService.on(WebsocketMessageType.PLAN_APPROVAL_REQUEST, (approvalRequest: any) => {
            console.log('📋 Plan received:', approvalRequest);

            let mPlanData: MPlanData | null = null;

            // Handle the different message structures
            if (approvalRequest.parsedData) {
                // Direct parsedData property
                mPlanData = approvalRequest.parsedData;
            } else if (approvalRequest.data && typeof approvalRequest.data === 'object') {
                // Data property with nested object
                if (approvalRequest.data.parsedData) {
                    mPlanData = approvalRequest.data.parsedData;
                } else {
                    // Try to parse the data object directly
                    mPlanData = approvalRequest.data;
                }
            } else if (approvalRequest.rawData) {
                // Parse the raw data string
                mPlanData = PlanDataService.parsePlanApprovalRequest(approvalRequest.rawData);
            } else {
                // Try to parse the entire object
                mPlanData = PlanDataService.parsePlanApprovalRequest(approvalRequest);
            }

            if (mPlanData) {
                console.log('✅ Parsed plan data:', mPlanData);
                setPlanApprovalRequest(mPlanData);
                setWaitingForPlan(false);
                setShowProcessingPlanSpinner(false);
                scrollToBottom();
            } else {
                console.error('❌ Failed to parse plan data', approvalRequest);
            }
        });

        return () => unsubscribe();
    }, [scrollToBottom]);

    //(WebsocketMessageType.AGENT_MESSAGE_STREAMING
    useEffect(() => {
        const unsubscribe = webSocketService.on(WebsocketMessageType.AGENT_MESSAGE_STREAMING, (streamingMessage: any) => {
            
            //console.log('📋 Streaming Message', streamingMessage);
            // if is final true clear buffer and add final message to agent messages
            const line = PlanDataService.simplifyHumanClarification(streamingMessage.data.content);
            setShowBufferingText(true);
            setStreamingMessageBuffer(prev => prev + line);
            //scrollToBottom();

        });

        return () => unsubscribe();
    }, [scrollToBottom]);

    //WebsocketMessageType.USER_CLARIFICATION_REQUEST
    useEffect(() => {
        const unsubscribe = webSocketService.on(WebsocketMessageType.USER_CLARIFICATION_REQUEST, (clarificationMessage: any) => {
            console.log('📋 Clarification Message', clarificationMessage);
            console.log('📋 Current plan data User clarification', planData);
            if (!clarificationMessage) {
                console.warn('⚠️ clarification message missing data:', clarificationMessage);
                return;
            }
            const agentMessageData = {
                agent: AgentType.GROUP_CHAT_MANAGER,
                agent_type: AgentMessageType.AI_AGENT,
                timestamp: clarificationMessage.timestamp || Date.now(),
                steps: [],   // intentionally always empty
                next_steps: [],  // intentionally always empty
                content: clarificationMessage.data.question || '',
                raw_data: clarificationMessage.data || '',
            } as AgentMessageData;
            console.log('✅ Parsed clarification message:', agentMessageData);
            setClarificationMessage(clarificationMessage.data as ParsedUserClarification | null);
            setAgentMessages(prev => [...prev, agentMessageData]);
            setShowBufferingText(false);
            setShowProcessingPlanSpinner(false);
            setSubmittingChatDisableInput(false);
            scrollToBottom();
            // Persist the agent message
            processAgentMessage(agentMessageData, planData);

        });

        return () => unsubscribe();
    }, [scrollToBottom, planData, processAgentMessage]);
    //WebsocketMessageType.AGENT_TOOL_MESSAGE
    useEffect(() => {
        const unsubscribe = webSocketService.on(WebsocketMessageType.AGENT_TOOL_MESSAGE, (toolMessage: any) => {
            console.log('📋 Tool Message', toolMessage);
            // scrollToBottom()

        });

        return () => unsubscribe();
    }, [scrollToBottom]);


    //WebsocketMessageType.FINAL_RESULT_MESSAGE
    useEffect(() => {
        const unsubscribe = webSocketService.on(WebsocketMessageType.FINAL_RESULT_MESSAGE, (finalMessage: any) => {
            console.log('📋 Final Result Message', finalMessage);
            if (!finalMessage) {

                console.warn('⚠️ Final result message missing data:', finalMessage);
                return;
            }
            const agentMessageData = {
                agent: AgentType.GROUP_CHAT_MANAGER,
                agent_type: AgentMessageType.AI_AGENT,
                timestamp: Date.now(),
                steps: [],   // intentionally always empty
                next_steps: [],  // intentionally always empty
                content: "🎉🎉 " + (finalMessage.data?.content || ''),
                raw_data: finalMessage || '',
            } as AgentMessageData;


            console.log('✅ Parsed final result message:', agentMessageData);
            // we ignore the terminated message 
            if (finalMessage?.data?.status === PlanStatus.COMPLETED) {

                setShowBufferingText(true);
                setShowProcessingPlanSpinner(false);
                setAgentMessages(prev => [...prev, agentMessageData]);
                setSelectedTeam(planData?.team || null);
                scrollToBottom();
                // Persist the agent message
                const is_final = true;
                if (planData?.plan) {
                    planData.plan.overall_status = PlanStatus.COMPLETED;
                    setPlanData({ ...planData });
                }

                // Wait for the agent message to be processed and persisted
                // The processAgentMessage function will handle refreshing the task list
                processAgentMessage(agentMessageData, planData, is_final, streamingMessageBuffer);

            }


        });

        return () => unsubscribe();
    }, [scrollToBottom, planData, processAgentMessage, streamingMessageBuffer, setSelectedTeam]);

    // WebsocketMessageType.ERROR_MESSAGE
    useEffect(() => {
        const unsubscribe = webSocketService.on(WebsocketMessageType.ERROR_MESSAGE, (errorMessage: any) => {
            console.log('❌ Received ERROR_MESSAGE:', errorMessage);
            console.log('❌ Error message data:', errorMessage?.data);
            
            // Try multiple ways to extract the error message
            let errorContent = "An unexpected error occurred. Please try again later.";
            
            // Check for double-nested data structure
            if (errorMessage?.data?.data?.content) {
                const content = errorMessage.data.data.content.trim();
                if (content.length > 0) {
                    errorContent = content;
                }
            } else if (errorMessage?.data?.content) {
                const content = errorMessage.data.content.trim();
                if (content.length > 0) {
                    errorContent = content;
                }
            } else if (errorMessage?.content) {
                const content = errorMessage.content.trim();
                if (content.length > 0) {
                    errorContent = content;
                }
            } else if (typeof errorMessage === 'string') {
                const content = errorMessage.trim();
                if (content.length > 0) {
                    errorContent = content;
                }
            }

            console.log('❌ Final error content to display:', errorContent);

            const errorAgentMessage: AgentMessageData = {
                agent: 'system',
                agent_type: AgentMessageType.SYSTEM_AGENT,
                timestamp: Date.now(),
                steps: [],
                next_steps: [],
                content: formatErrorMessage(errorContent),
                raw_data: errorMessage || '',
            };

            setAgentMessages(prev => [...prev, errorAgentMessage]);
            setShowProcessingPlanSpinner(false);
            setShowBufferingText(false);
            setIsProcessing(false);
            setShowProcessingMessage(false);
            setSubmittingChatDisableInput(false);
            scrollToBottom();
            showToast(errorContent, "error");
        });

        return () => unsubscribe();
    }, [scrollToBottom, showToast, formatErrorMessage]);

    //WebsocketMessageType.AGENT_MESSAGE
    useEffect(() => {
        const unsubscribe = webSocketService.on(WebsocketMessageType.AGENT_MESSAGE, (agentMessage: any) => {
            console.log('📋 Agent Message', agentMessage)
            console.log('📋 Current plan data', planData);
            const agentMessageData = agentMessage.data as AgentMessageData;
            if (agentMessageData) {
                agentMessageData.content = PlanDataService.simplifyHumanClarification(agentMessageData?.content);
                setAgentMessages(prev => [...prev, agentMessageData]);
                setShowProcessingPlanSpinner(true);
                scrollToBottom();
                processAgentMessage(agentMessageData, planData);
            }

        });

        return () => unsubscribe();
    }, [scrollToBottom, planData, processAgentMessage]); //onPlanReceived, scrollToBottom

    // Loading message rotation effect
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (loading) {
            let index = 0;
            interval = setInterval(() => {
                index = (index + 1) % loadingMessages.length;
                setLoadingMessage(loadingMessages[index]);
            }, 3000);
        }
        return () => clearInterval(interval);
    }, [loading]);

    // WebSocket connection with proper error handling and v3 backend compatibility
    useEffect(() => {
        if (planId && continueWithWebsocketFlow) {
            console.log('🔌 Connecting WebSocket:', { planId, continueWithWebsocketFlow });

            const connectWebSocket = async () => {
                try {
                    await webSocketService.connect(planId);
                    console.log('✅ WebSocket connected successfully');
                } catch (error) {
                    console.error('❌ WebSocket connection failed:', error);
                    // Continue without WebSocket - the app should still work
                }
            };

            connectWebSocket();

            const handleConnectionChange = (connected: boolean) => {
                setWsConnected(connected);
                console.log('🔗 WebSocket connection status:', connected);
            };

            const handleStreamingMessage = (message: StreamMessage) => {
                console.log('📨 Received streaming message:', message);
                if (message.data && message.data.plan_id) {
                    setStreamingMessages(prev => [...prev, message.data]);
                }
            };

            const handlePlanApprovalResponse = (message: StreamMessage) => {
                console.log('✅ Plan approval response received:', message);
                if (message.data && message.data.approved) {
                    setPlanApproved(true);
                }
            };

            const handlePlanApprovalRequest = (message: StreamMessage) => {
                console.log('📥 Plan approval request received:', message);
                // This is handled by PlanChat component through its own listener
            };

            // Subscribe to all relevant v3 backend events
            const unsubscribeConnection = webSocketService.on('connection_status', (message) => {
                handleConnectionChange(message.data?.connected || false);
            });

            const unsubscribeStreaming = webSocketService.on(WebsocketMessageType.AGENT_MESSAGE, handleStreamingMessage);
            const unsubscribePlanApproval = webSocketService.on(WebsocketMessageType.PLAN_APPROVAL_RESPONSE, handlePlanApprovalResponse);
            const unsubscribePlanApprovalRequest = webSocketService.on(WebsocketMessageType.PLAN_APPROVAL_REQUEST, handlePlanApprovalRequest);
            const unsubscribeParsedPlanApprovalRequest = webSocketService.on(WebsocketMessageType.PLAN_APPROVAL_REQUEST, handlePlanApprovalRequest);

            return () => {
                console.log('🔌 Cleaning up WebSocket connections');
                unsubscribeConnection();
                unsubscribeStreaming();
                unsubscribePlanApproval();
                unsubscribePlanApprovalRequest();
                unsubscribeParsedPlanApprovalRequest();
                webSocketService.disconnect();
            };
        }
    }, [planId, loading, continueWithWebsocketFlow]);

    // Create loadPlanData function with useCallback to memoize it
    const loadPlanData = useCallback(
        async (useCache = true): Promise<ProcessedPlanData | null> => {
            if (!planId) return null;
            resetPlanVariables();
            setLoading(true);
            try {

                let planResult: ProcessedPlanData | null = null;
                console.log("Fetching plan with ID:", planId);
                planResult = await PlanDataService.fetchPlanData(planId, useCache);
                console.log("Plan data fetched:", planResult);
                if (planResult?.plan?.overall_status === PlanStatus.IN_PROGRESS) {
                    setShowApprovalButtons(true);

                } else {
                    setShowApprovalButtons(false);
                    setWaitingForPlan(false);
                }
                if (planResult?.plan?.overall_status !== PlanStatus.COMPLETED) {
                    setContinueWithWebsocketFlow(true);
                }
                if (planResult?.messages) {
                    setAgentMessages(planResult.messages);
                }
                if (planResult?.mplan) {
                    setPlanApprovalRequest(planResult.mplan);
                }
                if (planResult?.streaming_message && planResult.streaming_message.trim() !== "") {
                    setStreamingMessageBuffer(planResult.streaming_message);
                    setShowBufferingText(true);
                }
                setPlanData(planResult);
                return planResult;
            } catch (err) {
                console.log("Failed to load plan data:", err);
                setErrorLoading(true);
                setPlanData(null);
                return null;
            } finally {
                setLoading(false);
            }
        },
        [planId, navigate, resetPlanVariables]
    );


    // Handle plan approval
    const handleApprovePlan = useCallback(async () => {
        if (!planApprovalRequest) return;

        setIsProcessing(true);
        setShowProcessingMessage(true);
        setProcessingApproval(true);
        let id = showToast("Submitting Approval", "progress");

        try {
            await apiService.approvePlan({
                m_plan_id: planApprovalRequest.id,
                plan_id: planData?.plan?.id,
                approved: true,
                feedback: 'Plan approved by user'
            });
            
            dismissToast(id);
            setShowProcessingPlanSpinner(true);
            setShowApprovalButtons(false);
            setIsProcessing(false);
            setShowProcessingMessage(false);

        } catch (error) {
            dismissToast(id);
            showToast("Failed to submit approval", "error");
            console.error('❌ Failed to approve plan:', error);
            setIsProcessing(false);
            setShowProcessingMessage(false);
        } finally {
            setProcessingApproval(false);
        }
    }, [planApprovalRequest, planData, setProcessingApproval]);

    // Handle plan rejection  
    const handleRejectPlan = useCallback(async () => {
        if (!planApprovalRequest) return;

        setProcessingApproval(true);
        let id = showToast("Submitting cancellation", "progress");
        try {
            await apiService.approvePlan({
                m_plan_id: planApprovalRequest.id,
                plan_id: planData?.plan?.id,
                approved: false,
                feedback: 'Plan rejected by user'
            });

            dismissToast(id);

            navigate('/');

        } catch (error) {
            dismissToast(id);
            showToast("Failed to submit cancellation", "error");
            console.error('❌ Failed to reject plan:', error);
            navigate('/');
        } finally {
            setProcessingApproval(false);
        }
    }, [planApprovalRequest, planData, navigate, setProcessingApproval]);
    // Chat submission handler - updated for v3 backend compatibility

    const handleOnchatSubmit = useCallback(
        async (chatInput: string) => {
            if (!chatInput.trim()) {
                showToast("Please enter a clarification", "error");
                return;
            }
            setInput("");

            if (!planData?.plan) return;
            setSubmittingChatDisableInput(true);
            let id = showToast("Submitting clarification", "progress");

            try {
                // Use legacy method for non-v3 backends
                const response = await PlanDataService.submitClarification({
                    request_id: clarificationMessage?.request_id || "",
                    answer: chatInput,
                    plan_id: planData?.plan.id,
                    m_plan_id: planApprovalRequest?.id || ""
                });

                console.log("Clarification submitted successfully:", response);
                setInput("");
                dismissToast(id);
                showToast("Clarification submitted successfully", "success");

                const agentMessageData = {
                    agent: 'human',
                    agent_type: AgentMessageType.HUMAN_AGENT,
                    timestamp: Date.now(),
                    steps: [],   // intentionally always empty
                    next_steps: [],  // intentionally always empty
                    content: chatInput || '',
                    raw_data: chatInput || '',
                } as AgentMessageData;

                setAgentMessages(prev => [...prev, agentMessageData]);
                setSubmittingChatDisableInput(true);
                setShowProcessingPlanSpinner(true);
                scrollToBottom();

            } catch (error: any) {
                setShowProcessingPlanSpinner(false);
                dismissToast(id);
                setSubmittingChatDisableInput(false);
                showToast(
                    "Failed to submit clarification",
                    "error"
                );

            } finally {

            }
        },
        [planData?.plan, showToast, dismissToast, loadPlanData]
    );


    // ✅ Handlers for PlanPanelLeft with plan cancellation protection
    const handleNewTaskButton = useCallback(() => {
        handleNavigationWithAlert(() => {
            navigate("/", { state: { focusInput: true } });
        });
    }, [navigate, handleNavigationWithAlert]);


    const resetReload = useCallback(() => {
        setReloadLeftList(false);
    }, []);

    useEffect(() => {
        const initializePlanLoading = async () => {
            if (!planId) {
                resetPlanVariables();
                setErrorLoading(true);
                return;
            }

            try {
                await loadPlanData(false);
            } catch (err) {
                console.error("Failed to initialize plan loading:", err);
            }
        };

        initializePlanLoading();
    }, [planId, loadPlanData, resetPlanVariables, setErrorLoading]);

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
                {/* ✅ RESTORED: PlanPanelLeft for navigation */}
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
                            >
                                {/* <PanelRightToggles>
                                    <TaskListSquareLtr />
                                </PanelRightToggles> */}
                            </ContentToolbar>
                            
                            <PlanChat
                                planData={planData}
                                OnChatSubmit={handleOnchatSubmit}
                                loading={loading}
                                setInput={setInput}
                                submittingChatDisableInput={submittingChatDisableInput}
                                input={input}
                                streamingMessages={streamingMessages}
                                wsConnected={wsConnected}
                                onPlanApproval={(approved) => setPlanApproved(approved)}
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
                    planData={planData}
                    loading={loading}
                    planApprovalRequest={planApprovalRequest}
                />
            </CoralShellRow>

            {/* Plan Cancellation Confirmation Dialog */}
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