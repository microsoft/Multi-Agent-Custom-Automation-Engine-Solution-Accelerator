import PanelLeft from "@/coral/components/Panels/PanelLeft";
import PanelLeftToolbar from "@/coral/components/Panels/PanelLeftToolbar";
import { Button, Spinner, Toast, ToastBody, ToastTitle, useToastController } from "@fluentui/react-components";
import { Add20Regular, ErrorCircle20Regular } from "@fluentui/react-icons";
import TaskList from "./TaskList";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PlanPanelLefProps, PlanWithSteps, Task } from "@/models";
import { apiService } from "@/api";
import { TaskService } from "@/services";

const PlanPanelLeft: React.FC<PlanPanelLefProps> = ({
    onNewTaskButton,
}) => {

    const { dispatchToast } = useToastController('toast');    // State for task lists
    const navigate = useNavigate();
    const [inProgressTasks, setInProgressTasks] = useState<Task[]>([]);
    const [completedTasks, setCompletedTasks] = useState<Task[]>([]);

    // State for API calls
    const [plans, setPlans] = useState<PlanWithSteps[] | null>(null);
    const [plansLoading, setPlansLoading] = useState<boolean>(false);
    const [plansError, setPlansError] = useState<Error | null>(null);

    /**
     * Load plans data and update task lists
     */
    const loadPlansData = useCallback(async (forceRefresh = false) => {
        try {
            setPlansLoading(true);
            setPlansError(null);

            // Call the apiService directly
            const plansData = await apiService.getPlans(undefined, !forceRefresh);
            setPlans(plansData);
        } catch (error) {
            console.error('Failed to load plans:', error);
            setPlansError(error instanceof Error ? error : new Error('Failed to load plans'));
        } finally {
            setPlansLoading(false);
        }
    }, []);

    // Load data on component mount
    useEffect(() => {
        loadPlansData();
    }, [loadPlansData]);


    const handleTaskSelect = useCallback((taskId: string) => {
        console.log('Selected task ID:', taskId);

        // Find the plan by session_id to get the plan_id
        const selectedPlan = plans?.find((plan: PlanWithSteps) => plan.session_id === taskId);
        if (selectedPlan) {
            navigate(`/plan/${selectedPlan.id}`);
        }
    }, [plans, navigate]);// Transform plans data when it changes
    useEffect(() => {
        if (plans) {
            const { inProgress, completed } = TaskService.transformPlansToTasks(plans);
            setInProgressTasks(inProgress);
            setCompletedTasks(completed);
        }
    }, [plans]);


    // Handle API errors
    useEffect(() => {
        if (plansError) {
            dispatchToast(
                <Toast>
                    <ToastTitle>
                        <ErrorCircle20Regular />
                        Failed to load tasks
                    </ToastTitle>
                    <ToastBody>
                        {plansError.message}
                    </ToastBody>
                </Toast>,
                { intent: 'error' }
            );
        }
    }, [plansError, dispatchToast]);

    return (
        <div style={{ flexShrink: 0, display: "flex", overflow: "hidden" }}>
            <PanelLeft
                panelWidth={280}
                panelResize={true}>
                <PanelLeftToolbar panelTitle="Tasks" panelIcon={null}>
                    <Button
                        icon={<Add20Regular />}
                        onClick={onNewTaskButton}
                        disabled={plansLoading}
                    >
                        New task
                    </Button>
                </PanelLeftToolbar>
                {plansLoading && (!inProgressTasks.length && !completedTasks.length) ? (
                    <div style={{ padding: '20px', textAlign: 'center' }}>
                        <Spinner size="medium" label="Loading tasks..." />
                    </div>
                ) : (
                    <TaskList
                        inProgressTasks={inProgressTasks}
                        completedTasks={completedTasks}
                        onTaskSelect={handleTaskSelect}
                    />
                )}
            </PanelLeft>
        </div>
    );
};

export default PlanPanelLeft; 