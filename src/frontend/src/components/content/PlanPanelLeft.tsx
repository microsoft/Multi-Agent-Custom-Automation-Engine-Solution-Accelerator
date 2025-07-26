import PanelLeft from "@/coral/components/Panels/PanelLeft";
import PanelLeftToolbar from "@/coral/components/Panels/PanelLeftToolbar";
import {
  Body1Strong,
  Button,
  Subtitle1,
  Subtitle2,
  Toast,
  ToastBody,
  ToastTitle,
  Tooltip,
  useToastController,
} from "@fluentui/react-components";
import {
  Add20Regular,
  ChatAdd20Regular,
  ErrorCircle20Regular,
} from "@fluentui/react-icons";
import TaskList from "./TaskList";
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PlanPanelLefProps, PlanWithSteps, Task, UserInfo } from "@/models";
import { apiService } from "@/api";
import { TaskService } from "@/services";
import MsftColor from "@/coral/imports/MsftColor";
import ContosoLogo from "../../coral/imports/ContosoLogo";
import "../../styles/PlanPanelLeft.css";
import PanelFooter from "@/coral/components/Panels/PanelFooter";
import PanelUserCard from "../../coral/components/Panels/UserCard";
import { getUserInfoGlobal } from "@/api/config";

const PlanPanelLeft: React.FC<PlanPanelLefProps> = ({ reloadTasks,restReload }) => {
  const { dispatchToast } = useToastController("toast");
  const navigate = useNavigate();
  const { planId } = useParams<{ planId: string }>();

  const [inProgressTasks, setInProgressTasks] = useState<Task[]>([]);
  const [completedTasks, setCompletedTasks] = useState<Task[]>([]);
  const [plans, setPlans] = useState<PlanWithSteps[] | null>(null);
  const [plansLoading, setPlansLoading] = useState<boolean>(false);
  const [plansError, setPlansError] = useState<Error | null>(null);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(
    getUserInfoGlobal()
  );

  const loadPlansData = useCallback(async (forceRefresh = false) => {
    try {
      setPlansLoading(true);
      setPlansError(null);
      const plansData = await apiService.getPlans(undefined, !forceRefresh);
      setPlans(plansData);
    } catch (error) {
      console.log("Failed to load plans:", error);
      setPlansError(
        error instanceof Error ? error : new Error("Failed to load plans")
      );
    } finally {
      setPlansLoading(false);
    }
  }, []);

  useEffect(() => {
    if (reloadTasks) {
      loadPlansData();
      restReload?.();
    }
  }, [reloadTasks, loadPlansData, restReload]);
  // Fetch plans
  

  useEffect(() => {
    loadPlansData();
  }, [loadPlansData]);

  useEffect(() => {
    if (plans) {
      const { inProgress, completed } =
        TaskService.transformPlansToTasks(plans);
      setInProgressTasks(inProgress);
      setCompletedTasks(completed);
    }
  }, [plans]);

  useEffect(() => {
    if (plansError) {
      dispatchToast(
        <Toast>
          <ToastTitle>
            <ErrorCircle20Regular />
            Failed to load tasks
          </ToastTitle>
          <ToastBody>{plansError.message}</ToastBody>
        </Toast>,
        { intent: "error" }
      );
    }
  }, [plansError, dispatchToast]);

  // Get the session_id that matches the current URL's planId
  const selectedTaskId =
    plans?.find((plan) => plan.id === planId)?.session_id ?? null;

  const handleTaskSelect = useCallback(
    (taskId: string) => {
      const selectedPlan = plans?.find(
        (plan: PlanWithSteps) => plan.session_id === taskId
      );
      if (selectedPlan) {
        navigate(`/plan/${selectedPlan.id}`);
      }
    },
    [plans, navigate]
  );

  return (
    <div style={{ flexShrink: 0, display: "flex", overflow: "hidden" }}>
      <PanelLeft panelWidth={280} panelResize={true}>
        <PanelLeftToolbar
          linkTo="/"
          panelTitle="DLM"
          panelIcon={<ContosoLogo />}
        >
          <Tooltip content="New task" relationship={"label"} />
        </PanelLeftToolbar>

        <br />
        <div
          className="tab tab-new-task"
          onClick={() => navigate("/", { state: { focusInput: true } })}
          tabIndex={0} // ✅ allows tab focus
          role="button" // ✅ announces as button
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              navigate("/", { state: { focusInput: true } });
            }
          }}
        >
          <div className="tab tab-new-task-icon">
            <ChatAdd20Regular />
          </div>
          <Body1Strong>New task</Body1Strong>
        </div>

        <br />
        <TaskList
          inProgressTasks={inProgressTasks}
          completedTasks={completedTasks}
          onTaskSelect={handleTaskSelect}
          loading={plansLoading}
          selectedTaskId={selectedTaskId ?? undefined}
        />

        <PanelFooter>
          <PanelUserCard
            name={userInfo ? userInfo.user_first_last_name : "Guest"}
            // alias={userInfo ? userInfo.user_email : ""}
            size={32}
          />
        </PanelFooter>
      </PanelLeft>
    </div>
  );
};

export default PlanPanelLeft;
