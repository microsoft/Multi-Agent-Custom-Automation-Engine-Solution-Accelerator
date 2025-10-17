import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Spinner, Text, Card, Body1 } from "@fluentui/react-components";
import { PlanDataService } from "../services/PlanDataService";
import { ProcessedPlanData, WebsocketMessageType, MPlanData, ParsedUserClarification, PlanStatus } from "../models";
import PlanPanelLeft from "../components/content/PlanPanelLeft";
import CoralShellColumn from "../coral/components/Layout/CoralShellColumn";
import CoralShellRow from "../coral/components/Layout/CoralShellRow";
import Content from "../coral/components/Content/Content";
import ContentToolbar from "../coral/components/Content/ContentToolbar";
import { useInlineToaster } from "../components/toast/InlineToaster";
import webSocketService from "../services/WebSocketService";
import { APIService } from "../api/apiService";
import SimplePlanApproval from "../components/content/SimplePlanApproval";
import SimpleProgressIndicator from "../components/content/SimpleProgressIndicator";
import SimplePlanChat from "../components/content/SimplePlanChat";
import { NewTaskService } from '../services/NewTaskService';

import "../styles/SimplePage.css";

const apiService = new APIService();

const SimplePlanPage: React.FC = () => {
    const { planId } = useParams<{ planId: string }>();
    const navigate = useNavigate();
    const { showToast, dismissToast } = useInlineToaster();
    
    const [planData, setPlanData] = useState<ProcessedPlanData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [errorLoading, setErrorLoading] = useState<boolean>(false);
    const [planApprovalRequest, setPlanApprovalRequest] = useState<MPlanData | null>(null);
    const [clarificationRequest, setClarificationRequest] = useState<ParsedUserClarification | null>(null);
    const [processingApproval, setProcessingApproval] = useState<boolean>(false);
    const [submittingClarification, setSubmittingClarification] = useState<boolean>(false);
    const [showApprovalButtons, setShowApprovalButtons] = useState<boolean>(true);
    const [isExecuting, setIsExecuting] = useState<boolean>(false);
    const [isCompleted, setIsCompleted] = useState<boolean>(false);
    const [completionMessage, setCompletionMessage] = useState<string>("");
    const [currentStep, setCurrentStep] = useState<number>(0);
    const [totalSteps, setTotalSteps] = useState<number>(0);
    const [reloadLeftList, setReloadLeftList] = useState<boolean>(true);
    const [selectedTeam, setSelectedTeam] = useState<any>(null);

    const resetPlanVariables = useCallback(() => {
        setPlanData(null);
        setLoading(true);
        setErrorLoading(false);
        setPlanApprovalRequest(null);
        setClarificationRequest(null);
        setProcessingApproval(false);
        setSubmittingClarification(false);
        setShowApprovalButtons(true);
        setIsExecuting(false);
        setIsCompleted(false);
        setCompletionMessage("");
        setCurrentStep(0);
        setTotalSteps(0);
    }, []);

    // WebSocket listener for plan approval request
    useEffect(() => {
        const unsubscribe = webSocketService.on(WebsocketMessageType.PLAN_APPROVAL_REQUEST, (approvalRequest: any) => {
            console.log('📋 Plan received:', approvalRequest);

            let mPlanData: MPlanData | null = null;

            if (approvalRequest.parsedData) {
                mPlanData = approvalRequest.parsedData;
            } else if (approvalRequest.data && typeof approvalRequest.data === 'object') {
                if (approvalRequest.data.parsedData) {
                    mPlanData = approvalRequest.data.parsedData;
                } else {
                    mPlanData = approvalRequest.data;
                }
            } else if (approvalRequest.rawData) {
                mPlanData = PlanDataService.parsePlanApprovalRequest(approvalRequest.rawData);
            } else {
                mPlanData = PlanDataService.parsePlanApprovalRequest(approvalRequest);
            }

            if (mPlanData) {
                console.log('✅ Parsed plan data:', mPlanData);
                setPlanApprovalRequest(mPlanData);
                setShowApprovalButtons(true);
                
                // Calculate total steps from steps array
                if (mPlanData.steps && mPlanData.steps.length > 0) {
                    setTotalSteps(mPlanData.steps.length);
                }
            } else {
                console.error('❌ Failed to parse plan data', approvalRequest);
            }
        });

        return () => unsubscribe();
    }, []);

    // WebSocket listener for user clarification request
    useEffect(() => {
        const unsubscribe = webSocketService.on(WebsocketMessageType.USER_CLARIFICATION_REQUEST, (clarificationMessage: any) => {
            console.log('📋 Clarification Message', clarificationMessage);
            
            if (!clarificationMessage) {
                console.warn('⚠️ clarification message missing data:', clarificationMessage);
                return;
            }
            
            setClarificationRequest(clarificationMessage.data as ParsedUserClarification | null);
            setSubmittingClarification(false);
        });

        return () => unsubscribe();
    }, []);

    // WebSocket listener for final result
    useEffect(() => {
        const unsubscribe = webSocketService.on(WebsocketMessageType.FINAL_RESULT_MESSAGE, (finalMessage: any) => {
            console.log('📋 Final Result Message', finalMessage);
            
            if (!finalMessage) {
                console.warn('⚠️ Final result message missing data:', finalMessage);
                return;
            }

            if (finalMessage?.data?.status === PlanStatus.COMPLETED) {
                setIsExecuting(false);
                setIsCompleted(true);
                setCompletionMessage(finalMessage.data?.content || 'Your request has been completed!');
                
                setTimeout(() => {
                    setReloadLeftList(true);
                }, 1000);
            }
        });

        return () => unsubscribe();
    }, []);

    // WebSocket listener for agent messages (to track progress)
    useEffect(() => {
        const unsubscribe = webSocketService.on(WebsocketMessageType.AGENT_MESSAGE, (agentMessage: any) => {
            console.log('📋 Agent Message (tracking progress)', agentMessage);
            
            // Increment progress when agent completes a task
            if (agentMessage?.data && totalSteps > 0) {
                setCurrentStep(prev => Math.min(prev + 1, totalSteps));
            }
        });

        return () => unsubscribe();
    }, [totalSteps]);

    // WebSocket connection
    useEffect(() => {
        if (planId) {
            console.log('🔌 Connecting WebSocket:', { planId });

            const connectWebSocket = async () => {
                try {
                    await webSocketService.connect(planId);
                    console.log('✅ WebSocket connected successfully');
                } catch (error) {
                    console.error('❌ WebSocket connection failed:', error);
                }
            };

            connectWebSocket();

            return () => {
                console.log('🔌 Cleaning up WebSocket connections');
                webSocketService.disconnect();
            };
        }
    }, [planId]);

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
                } else if (planResult?.plan?.overall_status === PlanStatus.COMPLETED) {
                    setIsCompleted(true);
                    setShowApprovalButtons(false);
                    // Get completion message from last message if available
                    if (planResult?.messages && planResult.messages.length > 0) {
                        const lastMessage = planResult.messages[planResult.messages.length - 1];
                        setCompletionMessage(lastMessage.content || 'Your request has been completed!');
                    }
                } else {
                    setShowApprovalButtons(false);
                }
                
                if (planResult?.mplan) {
                    setPlanApprovalRequest(planResult.mplan);
                    if (planResult.mplan.steps && planResult.mplan.steps.length > 0) {
                        setTotalSteps(planResult.mplan.steps.length);
                    }
                }
                
                setPlanData(planResult);
                setSelectedTeam(planResult?.team || null);
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

    const handleApprovePlan = useCallback(async () => {
        if (!planApprovalRequest) return;

        setProcessingApproval(true);
        let id = showToast("Starting your request...", "progress");
        
        try {
            await apiService.approvePlan({
                m_plan_id: planApprovalRequest.id,
                plan_id: planData?.plan?.id,
                approved: true,
                feedback: 'Plan approved by user'
            });

            dismissToast(id);
            setShowApprovalButtons(false);
            setIsExecuting(true);
            setClarificationRequest(null);
            setCurrentStep(0);
        } catch (error) {
            dismissToast(id);
            showToast("Failed to start request", "error");
            console.error('❌ Failed to approve plan:', error);
        } finally {
            setProcessingApproval(false);
        }
    }, [planApprovalRequest, planData, showToast, dismissToast]);

    const handleRejectPlan = useCallback(async () => {
        if (!planApprovalRequest) return;

        setProcessingApproval(true);
        let id = showToast("Cancelling request...", "progress");
        
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
            showToast("Failed to cancel request", "error");
            console.error('❌ Failed to reject plan:', error);
            navigate('/');
        } finally {
            setProcessingApproval(false);
        }
    }, [planApprovalRequest, planData, navigate, showToast, dismissToast]);

    const handleSubmitClarification = useCallback(
        async (answer: string) => {
            if (!planData?.plan || !clarificationRequest) return;
            
            setSubmittingClarification(true);
            let id = showToast("Submitting response...", "progress");

            try {
                await PlanDataService.submitClarification({
                    request_id: clarificationRequest?.request_id || "",
                    answer: answer,
                    plan_id: planData?.plan.id,
                    m_plan_id: planApprovalRequest?.id || ""
                });

                console.log("Clarification submitted successfully");
                dismissToast(id);
                showToast("Response submitted", "success");
                setClarificationRequest(null);
                setIsExecuting(true);
            } catch (error: any) {
                dismissToast(id);
                setSubmittingClarification(false);
                showToast("Failed to submit response", "error");
            }
        },
        [planData?.plan, clarificationRequest, planApprovalRequest, showToast, dismissToast]
    );

    const handleNewTaskButton = useCallback(() => {
        navigate("/", { state: { focusInput: true } });
    }, [navigate]);

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
                    />
                    <Content>
                        <div style={{
                            textAlign: "center",
                            padding: "40px 20px",
                            color: 'var(--colorNeutralForeground2)'
                        }}>
                            <Text size={500}>
                                {"An error occurred while loading your request"}
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
                />

                <Content>
                    {loading || !planData ? (
                        <div style={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            gap: "12px",
                            justifyContent: "center",
                            padding: "40px 20px",
                        }}>
                            <Spinner size="large" />
                            <Text>Loading your request...</Text>
                        </div>
                    ) : (
                        <>
                            <ContentToolbar
                                panelTitle="AI Assistant"
                            />

                            <div className="simple-plan-page__content">
                                {/* Plan Approval State */}
                                {showApprovalButtons && planApprovalRequest && !isExecuting && !isCompleted && (
                                    <SimplePlanApproval
                                        planData={planApprovalRequest}
                                        onApprove={handleApprovePlan}
                                        onReject={handleRejectPlan}
                                        processing={processingApproval}
                                    />
                                )}

                                {/* Execution State */}
                                {isExecuting && !clarificationRequest && !isCompleted && (
                                    <SimpleProgressIndicator
                                        currentStep={currentStep}
                                        totalSteps={totalSteps}
                                        message="Working on your request..."
                                    />
                                )}

                                {/* Clarification State */}
                                {clarificationRequest && !isCompleted && (
                                    <SimplePlanChat
                                        clarificationRequest={clarificationRequest}
                                        onSubmitClarification={handleSubmitClarification}
                                        disabled={submittingClarification}
                                    />
                                )}

                                {/* Completion State */}
                                {isCompleted && (
                                    <Card className="simple-completion">
                                        <div className="simple-completion__content">
                                            <Text size={500} weight="semibold">✅ All done!</Text>
                                            <Body1>{completionMessage}</Body1>
                                        </div>
                                    </Card>
                                )}
                            </div>
                        </>
                    )}
                </Content>
            </CoralShellRow>
        </CoralShellColumn>
    );
};

export default SimplePlanPage;

