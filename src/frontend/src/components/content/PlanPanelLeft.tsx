import PanelLeft from "@/coral/components/Panels/PanelLeft";
import PanelLeftToolbar from "@/coral/components/Panels/PanelLeftToolbar";
import {
  Body1Strong,
  Toast,
  ToastBody,
  ToastTitle,
  Tooltip,
  useToastController,
} from "@fluentui/react-components";
import {
  ChatAdd20Regular,
  ErrorCircle20Regular,
} from "@fluentui/react-icons";
import TaskList from "./TaskList";
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { Plan, PlanPanelLefProps, Task, UserInfo } from "@/models";
import { apiService } from "@/api";
import { TaskService } from "@/services";
import ContosoLogo from "../../coral/imports/ContosoLogo";
import "../../styles/PlanPanelLeft.css";
import PanelFooter from "@/coral/components/Panels/PanelFooter";
import PanelUserCard from "../../coral/components/Panels/UserCard";
import { getUserInfoGlobal } from "@/api/config";
import TeamSelector from "../common/TeamSelector";
import { TeamConfig } from "../../models/Team";
import TeamSelected from "../common/TeamSelected";
import TeamService from "@/services/TeamService";

const PlanPanelLeft: React.FC<PlanPanelLefProps> = ({
  reloadTasks,
  restReload,
  onTeamSelect,
  onTeamUpload,
  isHomePage,
  selectedTeam: parentSelectedTeam
}) => {
  const { dispatchToast } = useToastController("toast");
  const navigate = useNavigate();
  const location = useLocation();
  const { planId } = useParams<{ planId: string }>();
  
  // Detect if we're in advanced mode
  const isAdvancedMode = location.pathname.startsWith('/advanced');

  const [inProgressTasks, setInProgressTasks] = useState<Task[]>([]);
  const [completedTasks, setCompletedTasks] = useState<Task[]>([]);
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [plansLoading, setPlansLoading] = useState<boolean>(false);
  const [plansError, setPlansError] = useState<Error | null>(null);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(
    getUserInfoGlobal()
  );

  // Use parent's selected team if provided, otherwise use local state
  const [localSelectedTeam, setLocalSelectedTeam] = useState<TeamConfig | null>(null);
  const selectedTeam = parentSelectedTeam || localSelectedTeam;

  const loadPlansData = useCallback(async (forceRefresh = false) => {
    try {
      console.log("Loading plans, forceRefresh:", forceRefresh);
      setPlansLoading(true);
      setPlansError(null);
      const plansData = await apiService.getPlans(undefined, forceRefresh);
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


  // Fetch plans


  useEffect(() => {
    loadPlansData();
    setUserInfo(getUserInfoGlobal());
  }, [loadPlansData, setUserInfo]);


  useEffect(() => {
    console.log("Reload tasks changed:", reloadTasks);
    if (reloadTasks) {
      // Force refresh to get the latest data (pass false to bypass cache)
      loadPlansData(false).then(() => {
        // Reset the reload flag after loading
        if (restReload) {
          restReload();
        }
      });
    }
  }, [loadPlansData, setUserInfo, reloadTasks, restReload]);
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

  // Get the plan.id that matches the current URL's planId
  const selectedTaskId =
    plans?.find((plan) => plan.id === planId)?.id ?? null;

  const handleTaskSelect = useCallback(
    (taskId: string) => {
      const selectedPlan = plans?.find(
        (plan: Plan) => plan.id === taskId // Changed from session_id to id
      );
      if (selectedPlan) {
        // Navigate to the correct mode (advanced or simple)
        const planPath = isAdvancedMode 
          ? `/advanced/plan/${selectedPlan.id}` 
          : `/plan/${selectedPlan.id}`;
        navigate(planPath);
      }
    },
    [plans, navigate, isAdvancedMode]
  );

  const handleTeamSelect = useCallback(
    (team: TeamConfig | null) => {
      // Use parent's team select handler if provided, otherwise use local state
      loadPlansData();
      if (onTeamSelect) {
        onTeamSelect(team);
      } else {
        if (team) {
          setLocalSelectedTeam(team);
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
          // Handle team deselection (null case)
          setLocalSelectedTeam(null);
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
      }
    },
    [onTeamSelect, dispatchToast, loadPlansData]
  );

  return (
    <div style={{ flexShrink: 0, display: "flex", overflow: "hidden" }}>
      <PanelLeft panelWidth={280} panelResize={true}>
        <PanelLeftToolbar
          linkTo="/"
          panelTitle="Contoso"
          panelIcon={<ContosoLogo />}
        >
          <Tooltip content="New task" relationship={"label"} />
        </PanelLeftToolbar>

        {/* Team Selector right under the toolbar */}

        <div style={{ marginTop: '8px', marginBottom: '8px' }}>
          {isHomePage && (
            <TeamSelector
              onTeamSelect={handleTeamSelect}
              onTeamUpload={onTeamUpload}
              selectedTeam={selectedTeam}
              isHomePage={isHomePage}
            />
          )}

          {!isHomePage && (
            <TeamSelected
              selectedTeam={TeamService.getStoredTeam()}
            />
          )}

        </div>
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
          completedTasks={completedTasks}
          onTaskSelect={handleTaskSelect}
          loading={plansLoading}
          selectedTaskId={selectedTaskId ?? undefined}
        />

        <PanelFooter>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', width: '100%' }}>
            {/* User Card */}
            <PanelUserCard
              name={userInfo?.user_first_last_name || "Guest"}
              // alias={userInfo ? userInfo.user_email : ""}
              size={32}
            />
          </div>
        </PanelFooter>
      </PanelLeft>
    </div>
  );
};

export default PlanPanelLeft;
