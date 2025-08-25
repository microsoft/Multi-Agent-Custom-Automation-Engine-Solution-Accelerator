import React, { useCallback, useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
    Text,
    ToggleButton,
    Toast,
    ToastTitle,
    ToastBody,
    useToastController,
} from "@fluentui/react-components";
import "../styles/PlanPage.css";
import CoralShellColumn from "../coral/components/Layout/CoralShellColumn";
import CoralShellRow from "../coral/components/Layout/CoralShellRow";
import Content from "../coral/components/Content/Content";
import { NewTaskService } from "../services/NewTaskService";
import { PlanDataService } from "../services/PlanDataService";
import { Step, ProcessedPlanData } from "@/models";
import PlanPanelLeft from "@/components/content/PlanPanelLeft";
import ContentToolbar from "@/coral/components/Content/ContentToolbar";
import PlanChat from "@/components/content/PlanChat";
import PlanPanelRight from "@/components/content/PlanPanelRight";
import InlineToaster, {
    useInlineToaster,
} from "../components/toast/InlineToaster";
import Octo from "../coral/imports/Octopus.png"; // 🐙 Animated PNG loader
import PanelRightToggles from "@/coral/components/Header/PanelRightToggles";
import { TaskListSquareLtr } from "@/coral/imports/bundleicons";
import LoadingMessage, { loadingMessages } from "@/coral/components/LoadingMessage";
import { RAIErrorCard, RAIErrorData } from "../components/errors";
import { TeamConfig } from "../models/Team";
import { TeamService } from "../services/TeamService";
import { webSocketService, StreamMessage, StreamingPlanUpdate } from "../services/WebSocketService";

/**
 * Page component for displaying a specific plan
 * Accessible via the route /plan/{plan_id}
 */
const PlanPage: React.FC = () => {
    const { planId } = useParams<{ planId: string }>();
    const navigate = useNavigate();
    const { showToast, dismissToast } = useInlineToaster();
    const { dispatchToast } = useToastController("toast");

    const [input, setInput] = useState("");
    const [planData, setPlanData] = useState<ProcessedPlanData | any>(null);
    const [allPlans, setAllPlans] = useState<ProcessedPlanData[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [submittingChatDisableInput, setSubmitting] = useState<boolean>(false);
    const [error, setError] = useState<Error | null>(null);
    const [processingSubtaskId, setProcessingSubtaskId] = useState<string | null>(
        null
    );
    const [reloadLeftList, setReloadLeftList] = useState(true);
    const [raiError, setRAIError] = useState<RAIErrorData | null>(null);
    const [selectedTeam, setSelectedTeam] = useState<TeamConfig | null>(null);
    const [streamingMessages, setStreamingMessages] = useState<StreamingPlanUpdate[]>([]);
    const [wsConnected, setWsConnected] = useState<boolean>(false);

    const loadPlanDataRef = useRef<((navigate?: boolean) => Promise<void>) | null>(null);

    const [loadingMessage, setLoadingMessage] = useState(loadingMessages[0]);

    // WebSocket connection and streaming setup
    useEffect(() => {
        const initializeWebSocket = async () => {
            try {
                await webSocketService.connect();
                setWsConnected(true);
            } catch (error) {
                console.error('Failed to connect to WebSocket:', error);
                setWsConnected(false);
            }
        };

        initializeWebSocket();

        // Set up WebSocket event listeners
        const unsubscribeConnectionStatus = webSocketService.on('connection_status', (message: StreamMessage) => {
            setWsConnected(message.data?.connected || false);
        });

        const unsubscribePlanUpdate = webSocketService.on('plan_update', (message: StreamMessage) => {
            if (message.data && message.data.plan_id === planId) {
                console.log('Plan update received:', message.data);
                setStreamingMessages(prev => [...prev, message.data as StreamingPlanUpdate]);
                
                // Refresh plan data for major updates
                if (message.data.status === 'completed' && loadPlanDataRef.current) {
                    loadPlanDataRef.current(false);
                }
            }
        });

        const unsubscribeStepUpdate = webSocketService.on('step_update', (message: StreamMessage) => {
            if (message.data && message.data.plan_id === planId) {
                console.log('Step update received:', message.data);
                setStreamingMessages(prev => [...prev, message.data as StreamingPlanUpdate]);
            }
        });

        const unsubscribeAgentMessage = webSocketService.on('agent_message', (message: StreamMessage) => {
            if (message.data && message.data.plan_id === planId) {
                console.log('Agent message received:', message.data);
                setStreamingMessages(prev => [...prev, message.data as StreamingPlanUpdate]);
            }
        });

        const unsubscribeError = webSocketService.on('error', (message: StreamMessage) => {
            console.error('WebSocket error:', message.data);
            showToast('Connection error: ' + (message.data?.error || 'Unknown error'), 'error');
        });

        // Cleanup function
        return () => {
            unsubscribeConnectionStatus();
            unsubscribePlanUpdate();
            unsubscribeStepUpdate();
            unsubscribeAgentMessage();
            unsubscribeError();
            webSocketService.disconnect();
        };
    }, [planId, showToast]);

    // Subscribe to plan updates when planId changes
    useEffect(() => {
        if (planId && wsConnected) {
            console.log('Subscribing to plan updates for:', planId);
            webSocketService.subscribeToPlan(planId);

            return () => {
                webSocketService.unsubscribeFromPlan(planId);
            };
        }
    }, [planId, wsConnected]);

    // 🌀 Cycle loading messages while loading
    useEffect(() => {
        if (!loading) return;
        let index = 0;
        const interval = setInterval(() => {
            index = (index + 1) % loadingMessages.length;
            setLoadingMessage(loadingMessages[index]);
        }, 2000);
        return () => clearInterval(interval);
    }, [loading]);

    // Load default team on component mount
    useEffect(() => {
        const loadDefaultTeam = async () => {
            let defaultTeam = TeamService.getStoredTeam();
            if (defaultTeam) {
                setSelectedTeam(defaultTeam);
                console.log('Default team loaded from storage:', defaultTeam.name);
                return;
            }
            
            try {
                const teams = await TeamService.getUserTeams();
                console.log('All teams loaded:', teams);
                if (teams.length > 0) {
                    // Always prioritize "Business Operations Team" as default
                    const businessOpsTeam = teams.find(team => team.name === "Business Operations Team");
                    defaultTeam = businessOpsTeam || teams[0];
                    TeamService.storageTeam(defaultTeam);
                    setSelectedTeam(defaultTeam);
                    console.log('Default team loaded:', defaultTeam.name);
                }
            } catch (error) {
                console.error('Error loading default team:', error);
            }
        };

        loadDefaultTeam();
    }, []);


    useEffect(() => {
        const currentPlan = allPlans.find(
            (plan) => plan.plan.id === planId
        );
        setPlanData(currentPlan || null);
    }, [allPlans,planId]);

    const loadPlanData = useCallback(
        async (navigate: boolean = true) => {
            if (!planId) return;

            try {
                setInput(""); // Clear input on new load
                if (navigate) {
                    setPlanData(null);
                    setLoading(true);
                    setError(null);
                    setProcessingSubtaskId(null);
                }

                setError(null);
                const data = await PlanDataService.fetchPlanData(planId,navigate);
                let plans = [...allPlans];
                const existingIndex = plans.findIndex(p => p.plan.id === data.plan.id);
                if (existingIndex !== -1) {
                    plans[existingIndex] = data;
                } else {
                    plans.push(data);
                }
                setAllPlans(plans);
                //setPlanData(data);
            } catch (err) {
                console.log("Failed to load plan data:", err);
                setError(
                    err instanceof Error ? err : new Error("Failed to load plan data")
                );
            } finally {
                setLoading(false);
            }
        },
        [planId]
    );

    // Update the ref whenever loadPlanData changes
    useEffect(() => {
        loadPlanDataRef.current = loadPlanData;
    }, [loadPlanData]);

    const handleOnchatSubmit = useCallback(
        async (chatInput: string) => {

            if (!chatInput.trim()) {
                showToast("Please enter a clarification", "error");
                return;
            }
            setInput("");
            setRAIError(null); // Clear any previous RAI errors
            if (!planData?.plan) return;
            setSubmitting(true);
            let id = showToast("Submitting clarification", "progress");
            try {
                await PlanDataService.submitClarification(
                    planData.plan.id,
                    planData.plan.session_id,
                    chatInput
                );
                setInput("");
                dismissToast(id);
                showToast("Clarification submitted successfully", "success");
                await loadPlanData(false);
            } catch (error: any) {
                dismissToast(id);
                
                // Check if this is an RAI validation error
                let errorDetail = null;
                try {
                    // Try to parse the error detail if it's a string
                    if (typeof error?.response?.data?.detail === 'string') {
                        errorDetail = JSON.parse(error.response.data.detail);
                    } else {
                        errorDetail = error?.response?.data?.detail;
                    }
                } catch (parseError) {
                    // If parsing fails, use the original error
                    errorDetail = error?.response?.data?.detail;
                }

                // Handle RAI validation errors with better UX
                if (errorDetail?.error_type === 'RAI_VALIDATION_FAILED') {
                    setRAIError(errorDetail);
                } else {
                    // Handle other errors with toast messages
                    showToast("Failed to submit clarification", "error");
                }
            } finally {
                setInput("");
                setSubmitting(false);
            }
        },
        [planData, loadPlanData]
    );

    const handleApproveStep = useCallback(
        async (step: Step, total: number, completed: number, approve: boolean) => {
            setProcessingSubtaskId(step.id);
            const toastMessage = approve ? "Approving step" : "Rejecting step";
            let id = showToast(toastMessage, "progress");
            setSubmitting(true);
            try {
                let approveRejectDetails = await PlanDataService.stepStatus(step, approve);
                dismissToast(id);
                showToast(`Step ${approve ? "approved" : "rejected"} successfully`, "success");
                if (approveRejectDetails && Object.keys(approveRejectDetails).length > 0) {
                    await loadPlanData(false);
                }
                setReloadLeftList(true);
            } catch (error) {
                dismissToast(id);
                showToast(`Failed to ${approve ? "approve" : "reject"} step`, "error");
            } finally {
                setProcessingSubtaskId(null);
                setSubmitting(false);
            }
        },
        [loadPlanData]
    );


    useEffect(() => {
        loadPlanData(true);
    }, [loadPlanData]);

    const handleNewTaskButton = () => {
        NewTaskService.handleNewTaskFromPlan(navigate);
    };

    /**
     * Handle team selection from the TeamSelector
     */
    const handleTeamSelect = useCallback((team: TeamConfig | null) => {
        setSelectedTeam(team);
        if (team) {
            dispatchToast(
                <Toast>
                    <ToastTitle>Team Selected</ToastTitle>
                    <ToastBody>
                        {team.name} team has been selected with {team.agents.length} agents
                    </ToastBody>
                </Toast>,
                { intent: "success" }
            );
        } else {
            dispatchToast(
                <Toast>
                    <ToastTitle>Team Deselected</ToastTitle>
                    <ToastBody>
                        No team is currently selected
                    </ToastBody>
                </Toast>,
                { intent: "info" }
            );
        }
    }, [dispatchToast]);

    /**
     * Handle team upload completion - refresh team list
     */
    const handleTeamUpload = useCallback(async () => {
        try {
            const teams = await TeamService.getUserTeams();
            console.log('Teams refreshed after upload:', teams.length);

            if (teams.length > 0) {
                // Always keep "Business Operations Team" as default, even after new uploads
                const businessOpsTeam = teams.find(team => team.name === "Business Operations Team");
                const defaultTeam = businessOpsTeam || teams[0];
                setSelectedTeam(defaultTeam);
                console.log('Default team after upload:', defaultTeam.name);
                
                dispatchToast(
                    <Toast>
                        <ToastTitle>Team Uploaded Successfully!</ToastTitle>
                        <ToastBody>
                            Team uploaded. {defaultTeam.name} remains your default team.
                        </ToastBody>
                    </Toast>,
                    { intent: "success" }
                );
            }
        } catch (error) {
            console.error('Error refreshing teams after upload:', error);
        }
    }, [dispatchToast]);

    if (!planId) {
        return (
            <div style={{ padding: "20px" }}>
                <Text>Error: No plan ID provided</Text>
            </div>
        );
    }

    return (
        <CoralShellColumn>
            <CoralShellRow>
                <PlanPanelLeft 
                    onNewTaskButton={handleNewTaskButton} 
                    reloadTasks={reloadLeftList} 
                    restReload={() => setReloadLeftList(false)}
                    onTeamSelect={handleTeamSelect}
                    onTeamUpload={handleTeamUpload}
                    selectedTeam={selectedTeam}
                />

                <Content>
                    {/* 🐙 Only replaces content body, not page shell */}
                    {loading ? (
                        <>
                            <LoadingMessage
                                loadingMessage={loadingMessage}
                                iconSrc={Octo}
                            />
                        </>
                    ) : (
                        <>
                            <ContentToolbar
                                panelTitle="Multi-Agent Planner"
                            // panelIcon={<ChatMultiple20Regular />}
                            >
                                <PanelRightToggles>
                                    <ToggleButton
                                        appearance="transparent"
                                        icon={<TaskListSquareLtr />}
                                    />
                                </PanelRightToggles>
                            </ContentToolbar>
                            
                            {/* Show RAI error if present */}
                            {raiError && (
                                <div style={{ padding: '16px 24px 0' }}>
                                    <RAIErrorCard
                                        error={raiError}
                                        onRetry={() => {
                                            setRAIError(null);
                                        }}
                                        onDismiss={() => setRAIError(null)}
                                    />
                                </div>
                            )}
                            
                            <PlanChat
                                planData={planData}
                                OnChatSubmit={handleOnchatSubmit}
                                loading={loading}
                                setInput={setInput}
                                submittingChatDisableInput={submittingChatDisableInput}
                                input={input}
                                streamingMessages={streamingMessages}
                                wsConnected={wsConnected}
                            />
                        </>
                    )}
                </Content>

                <PlanPanelRight
                    planData={planData}
                    OnApproveStep={handleApproveStep}
                    submittingChatDisableInput={submittingChatDisableInput}
                    processingSubtaskId={processingSubtaskId}
                    loading={loading}
                />
            </CoralShellRow>
        </CoralShellColumn>
    );
};

export default PlanPage;