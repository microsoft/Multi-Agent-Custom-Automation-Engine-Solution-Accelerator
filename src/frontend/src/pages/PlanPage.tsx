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

/**
 * Page component for displaying a specific plan
 * Accessible via the route /plan/{plan_id}
 */
const PlanPage: React.FC = () => {
    const { planId } = useParams<{ planId: string }>();
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
                await loadPlanData(false);
            } catch (error) {
                dismissToast(id);
                showToast("Failed to submit clarification", "error");
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

export default PlanPage;
