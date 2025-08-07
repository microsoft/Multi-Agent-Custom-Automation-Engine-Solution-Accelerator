import React, { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
    Text,
    ToggleButton,
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
import { apiClient } from "../api/apiClient";
import { TeamConfig } from "../models/Team";
import { TeamService } from "../services/TeamService";

/**
 * Page component for creating and viewing a plan being generated
 * Accessible via the route /plan/{plan_id}/create/{team_id?}
 */
const PlanCreatePage: React.FC = () => {
    const { planId, teamId } = useParams<{ planId: string; teamId?: string }>();
    const navigate = useNavigate();
    const { showToast, dismissToast } = useInlineToaster();

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
    const [planGenerated, setPlanGenerated] = useState<boolean>(false);
    const [selectedTeam, setSelectedTeam] = useState<TeamConfig | null>(null);

    const [loadingMessage, setLoadingMessage] = useState(loadingMessages[0]);

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

    // Load team data if teamId is provided
    useEffect(() => {
        const loadTeamData = async () => {
            if (teamId) {
                console.log('Loading team data for ID:', teamId);
                try {
                    const team = await TeamService.getTeamById(teamId);
                    if (team) {
                        setSelectedTeam(team);
                        console.log('Team loaded for plan creation:', team.name);
                    } else {
                        console.warn('Team not found for ID:', teamId);
                    }
                } catch (error) {
                    console.error('Error loading team data:', error);
                }
            }
        };
        
        loadTeamData();
    }, [teamId]);

    useEffect(() => {
        const currentPlan = allPlans.find(
            (plan) => plan.plan.id === planId
        );
        setPlanData(currentPlan || null);
    }, [allPlans, planId]);

    const generatePlan = useCallback(async () => {
        if (!planId) return;

        try {
            setLoading(true);
            setError(null);
            
            let toastId = showToast("Generating plan steps...", "progress");
            
            // Call the generate_plan endpoint using apiClient for proper authentication
            const result = await apiClient.post('/generate_plan', {
                plan_id: planId
            });

            dismissToast(toastId);
            showToast("Plan generated successfully!", "success");
            setPlanGenerated(true);
            
            // Now load the plan data to display it
            await loadPlanData(false);
            
        } catch (err) {
            console.error("Failed to generate plan:", err);
            setError(
                err instanceof Error ? err : new Error("Failed to generate plan")
            );
            setLoading(false);
        }
    }, [planId, showToast, dismissToast]);

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
                const data = await PlanDataService.fetchPlanData(planId, navigate);
                let plans = [...allPlans];
                const existingIndex = plans.findIndex(p => p.plan.id === data.plan.id);
                if (existingIndex !== -1) {
                    plans[existingIndex] = data;
                } else {
                    plans.push(data);
                }
                setAllPlans(plans);
                
                // If plan has steps and we haven't generated yet, mark as generated
                if (data.plan.steps && data.plan.steps.length > 0 && !planGenerated) {
                    setPlanGenerated(true);
                }
                
            } catch (err) {
                console.log("Failed to load plan data:", err);
                setError(
                    err instanceof Error ? err : new Error("Failed to load plan data")
                );
            } finally {
                setLoading(false);
            }
        },
        [planId, allPlans, planGenerated]
    );

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
        const initializePage = async () => {
            // Load the basic plan data first
            await loadPlanData(true);
        };
        
        initializePage();
    }, []);

    // Separate effect for plan generation when plan data is loaded
    useEffect(() => {
        if (planData && (!planData.plan.steps || planData.plan.steps.length === 0) && !planGenerated && !loading) {
            generatePlan();
        }
    }, [planData, planGenerated, loading]);

    const handleNewTaskButton = () => {
        NewTaskService.handleNewTaskFromPlan(navigate);
    };

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
                    restReload={()=>setReloadLeftList(false)}
                    selectedTeam={selectedTeam}
                />

                <Content>
                    {/* 🐙 Only replaces content body, not page shell */}
                    {loading ? (
                        <>
                            <LoadingMessage
                                loadingMessage={planGenerated ? loadingMessage : "Generating your plan..."}
                                iconSrc={Octo}
                            />
                        </>
                    ) : (
                        <>
                            <ContentToolbar
                                panelTitle={planData?.plan?.initial_goal || "Plan Creation"}
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

export default PlanCreatePage;
