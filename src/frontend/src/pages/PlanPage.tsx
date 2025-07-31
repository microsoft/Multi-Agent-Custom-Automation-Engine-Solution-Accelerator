import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, useLocation } from "react-router-dom";
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
import { apiService } from "../api/apiService";
import { Step, ProcessedPlanData } from "@/models";
import PlanPanelLeft from "@/components/content/PlanPanelLeft";
import ContentToolbar from "@/coral/components/Content/ContentToolbar";
import PlanChat from "@/components/content/PlanChat";
import PlanStreamingChat from "@/components/content/PlanStreamingChat";
import PlanPanelRight from "@/components/content/PlanPanelRight";
import InlineToaster, {
    useInlineToaster,
} from "../components/toast/InlineToaster";
import Octo from "../coral/imports/Octopus.png"; // 🐙 Animated PNG loader
import PanelRightToggles from "@/coral/components/Header/PanelRightToggles";
import { TaskListSquareLtr } from "@/coral/imports/bundleicons";
import LoadingMessage, { loadingMessages } from "@/coral/components/LoadingMessage";

/**
 * Page component for displaying a specific plan
 * Accessible via the route /plan/{plan_id}
 */
const PlanPage: React.FC = () => {
    const { planId } = useParams<{ planId: string }>();
    const navigate = useNavigate();
    const location = useLocation();
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
    const [loadingMessage, setLoadingMessage] = useState(loadingMessages[0]);
    const streamingChatRef = useRef<any>(null); // Ref to access streaming chat methods
    const [isStepApprovalInProgress, setIsStepApprovalInProgress] = useState(false); // Track step approval state
    
    // New state for streaming functionality
    const [isNewPlan, setIsNewPlan] = useState<boolean>(false);
    const [showStreaming, setShowStreaming] = useState<boolean>(false);
    const [streamingComplete, setStreamingComplete] = useState<boolean>(false);
    const [streamingStarted, setStreamingStarted] = useState<boolean>(false); // Add flag to track if streaming started
    
    // Use a ref to track which plan ID we've already initiated streaming for
    const streamingInitiatedForPlan = useRef<string | null>(null);

    // Reset streaming state when planId changes
    useEffect(() => {
        if (planId !== streamingInitiatedForPlan.current) {
            setStreamingStarted(false);
            setStreamingComplete(false);
            setShowStreaming(false);
            streamingInitiatedForPlan.current = null;
        }
    }, [planId]);

    // Check if this is a new plan that needs streaming
    useEffect(() => {
        const state = location.state as any;
        const isCreateRoute = location.pathname.endsWith('/create');
        
        if ((state?.isNewPlan && state?.autoStartGeneration) || isCreateRoute) {
            setIsNewPlan(true);
            setShowStreaming(true);
            setStreamingStarted(true); // Mark that streaming was initiated
        }
    }, [location.state, location.pathname]);

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


    useEffect(() => {
        const currentPlan = allPlans.find(
            (plan) => plan.plan.id === planId
        );
        setPlanData(currentPlan || null);
        
        // Check if this is a new plan without steps and show streaming (only if not already started)
        if (currentPlan && 
            planId &&
            (!currentPlan.steps || currentPlan.steps.length === 0) && 
            !streamingComplete && 
            !streamingStarted &&
            streamingInitiatedForPlan.current !== planId) {
            
            console.log(`Initiating streaming for plan ${planId}`);
            setShowStreaming(true);
            setStreamingStarted(true);
            streamingInitiatedForPlan.current = planId; // Mark this plan as having streaming initiated
        }
    }, [allPlans, planId, streamingComplete, streamingStarted]);

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
                } else {
                    // For streaming, only clear error but keep existing planData
                    setError(null);
                }

                setError(null);
                const data = await PlanDataService.fetchPlanData(planId,navigate);
                // Set planData for both streaming and non-streaming scenarios
                setPlanData(data);
                
                setAllPlans(prevPlans => {
                    const plans = [...prevPlans];
                    const existingIndex = plans.findIndex(p => p.plan.id === data.plan.id);
                    if (existingIndex !== -1) {
                        plans[existingIndex] = data;
                    } else {
                        plans.push(data);
                    }
                    return plans;
                });
            } catch (err) {
                console.log("Failed to load plan data:", err);
                setError(
                    err instanceof Error ? err : new Error("Failed to load plan data")
                );
            } finally {
                setLoading(false);
            }
        },
        [planId] // Removed allPlans dependency to prevent unnecessary recreations
    );

    const handleOnchatSubmit = useCallback(
        async (chatInput: string) => {

            if (!chatInput.trim()) {
                showToast("Please enter a clarification", "error");
                return;
            }
            setInput("");
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
                // Only reload plan data if not currently streaming
                if (!showStreaming && !streamingStarted) {
                    await loadPlanData(false);
                }
            } catch (error) {
                dismissToast(id);
                showToast("Failed to submit clarification", "error");
                console.log("Failed to submit clarification:", error);
            } finally {
                setInput("");
                setSubmitting(false);
            }
        },
        [planData, loadPlanData, showStreaming, streamingStarted]
    );

    const handleApproveStep = useCallback(
        async (step: Step, total: number, completed: number, approve: boolean) => {
            setProcessingSubtaskId(step.id);
            setIsStepApprovalInProgress(true); // Disable chat during approval
            const toastMessage = approve ? "Approving step" : "Rejecting step";
            let id = showToast(toastMessage, "progress");
            setSubmitting(true);
            try {
                // Use the streaming chat's step approval method if available
                if (streamingChatRef.current?.handleStepApproval) {
                    await streamingChatRef.current.handleStepApproval(step, total, completed, approve);
                } else {
                    // Fallback to direct API call (shouldn't happen normally)
                    const stream = await apiService.approveStepStreamNew(
                        step.id,
                        step.plan_id,
                        step.session_id,
                        approve
                    );

                    // Process the streaming response
                    const reader = stream.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || '';

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const data = line.slice(6);
                                if (data.trim() && data !== '[DONE]') {
                                    console.log('Agent response:', data);
                                }
                            }
                        }
                    }
                }

                dismissToast(id);
                showToast(`Step ${approve ? "approved" : "rejected"} successfully`, "success");
                
                // Always reload plan data after step approval to show updated status
                await loadPlanData(false);
                setReloadLeftList(true);
            } catch (error) {
                dismissToast(id);
                showToast(`Failed to ${approve ? "approve" : "reject"} step`, "error");
                console.log(`Failed to ${approve ? "approve" : "reject"} step:`, error);
            } finally {
                setProcessingSubtaskId(null);
                setSubmitting(false);
                setIsStepApprovalInProgress(false); // Re-enable chat after approval completes
            }
        },
        [loadPlanData, showStreaming, streamingStarted]
    );


    // Load plan data when planId changes (but avoid unnecessary API calls for cached plans)
    useEffect(() => {
        if (!planId) return;
        
        // Check if we already have this plan in allPlans (from previous navigation)
        const existingPlan = allPlans.find(plan => plan.plan.id === planId);
        
        if (existingPlan && !showStreaming && !streamingStarted) {
            // Use cached data for completed plans, no API call needed - just show the history
            console.log(`Using cached data for plan ${planId} - showing history without API call`);
            setPlanData(existingPlan);
            setLoading(false);
            setError(null);
            return;
        }
        
        // Only make API calls for new plans not in cache or when streaming
        if (!showStreaming && !streamingStarted) {
            console.log(`Loading new plan data for ${planId}`);
            loadPlanData(true);
        } else if (showStreaming || streamingStarted) {
            // For streaming plans, load basic plan data without clearing UI
            loadPlanData(false);
        }
    }, [planId, showStreaming, streamingStarted, allPlans]);

    const handleNewTaskButton = () => {
        NewTaskService.handleNewTaskFromPlan(navigate);
    };

    // Streaming handlers
    const handleStreamComplete = useCallback(async () => {
        setStreamingComplete(true);
        // Don't hide streaming chat - keep it visible to show the reasoning process
        // setShowStreaming(false); // REMOVED - keep reasoning visible
        setLoading(false); // Ensure loading is false
        setSubmitting(false); // Ensure chat input is not disabled
        showToast("Plan generation completed! You can now review and approve each step.", "success");
        
        // Reload plan data to show the generated steps
        await loadPlanData(false);
        setReloadLeftList(true);
        
        // Keep the URL as is - don't redirect automatically
        // Users can navigate manually if they want to change the URL
    }, [loadPlanData, showToast]);

    const handleStreamError = useCallback((error: string) => {
        setShowStreaming(false);
        showToast(`Plan generation failed: ${error}`, "error");
    }, [showToast]);

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
                <PlanPanelLeft onNewTaskButton={handleNewTaskButton} reloadTasks={reloadLeftList} restReload={()=>setReloadLeftList(false)}/>

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
                                panelTitle={planData?.plan?.initial_goal || "Plan Details"}
                            // panelIcon={<ChatMultiple20Regular />}
                            >
                                <PanelRightToggles>
                                    <ToggleButton
                                        appearance="transparent"
                                        icon={<TaskListSquareLtr />}
                                    />
                                </PanelRightToggles>
                            </ContentToolbar>
                            
                            {/* Always show streaming chat for plans - both during generation and after completion */}
                            {planId ? (
                                <PlanStreamingChat
                                    ref={streamingChatRef}
                                    planId={planId}
                                    onStreamComplete={handleStreamComplete}
                                    onStreamError={handleStreamError}
                                    onChatSubmit={handleOnchatSubmit}
                                    planData={planData}
                                    isStepApprovalInProgress={isStepApprovalInProgress}
                                />
                            ) : (
                                /* Fallback to regular chat if no planId */
                                <PlanChat
                                    planData={planData}
                                    OnChatSubmit={handleOnchatSubmit}
                                    loading={false}
                                    setInput={setInput}
                                    submittingChatDisableInput={false}
                                    input={input}
                                />
                            )}
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
