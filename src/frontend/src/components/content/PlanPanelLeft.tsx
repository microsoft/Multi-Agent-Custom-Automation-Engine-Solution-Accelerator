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
import { useCallback, useEffect, useState, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Plan, PlanPanelLefProps, UserInfo } from "@/models";
import "../../styles/PlanPanelLeft.css";
import PanelFooter from "@/coral/components/Panels/PanelFooter";
import PanelUserCard from "../../coral/components/Panels/UserCard";
import { getUserInfoGlobal } from "@/api/config";
import TeamSelector from "../common/TeamSelector";
import { TeamConfig } from "../../models/Team";
import TeamSelected from "../common/TeamSelected";
import ContosoLogo from "../../coral/imports/ContosoLogo";
import { usePlanList } from "@/hooks/usePlanList";

const PlanPanelLeft: React.FC<PlanPanelLefProps> = ({
  reloadTasks,
  onNewTaskButton,
  restReload,
  onTeamSelect,
  onTeamUpload,
  isHomePage,
  selectedTeam: parentSelectedTeam,
  onNavigationWithAlert,
  isLoadingTeam
}) => {
  const { dispatchToast } = useToastController("toast");
  const navigate = useNavigate();
  const { planId } = useParams<{ planId: string }>();

  const [userInfo, setUserInfo] = useState<UserInfo | null>(getUserInfoGlobal());

  // Use parent's selected team if provided, otherwise use local state
  const [localSelectedTeam, setLocalSelectedTeam] = useState<TeamConfig | null>(null);
  const selectedTeam = parentSelectedTeam || localSelectedTeam;

  // ── Plan list hook ──
  const { plans, completedTasks, plansLoading, plansError, loadPlans } = usePlanList(
    reloadTasks,
    restReload
  );

  // Refresh user info on mount
  useEffect(() => {
    setUserInfo(getUserInfoGlobal());
  }, []);

  // Show error toast when plan loading fails
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

  // Get the session_id that matches the current URL's planId (memoized)
  const selectedTaskId = useMemo(
    () => plans?.find((plan) => plan.id === planId)?.session_id ?? null,
    [plans, planId]
  );

  const handleTaskSelect = useCallback(
    (taskId: string) => {
      const performNavigation = () => {
        const selectedPlan = plans?.find(
          (plan: Plan) => plan.session_id === taskId
        );
        if (selectedPlan) {
          navigate(`/plan/${selectedPlan.id}`);
        }
      };

      if (onNavigationWithAlert) {
        onNavigationWithAlert(performNavigation);
      } else {
        performNavigation();
      }
    },
    [plans, navigate, onNavigationWithAlert]
  );

  const handleLogoClick = useCallback(() => {
    const performNavigation = () => {
      navigate("/");
    };

    if (onNavigationWithAlert) {
      onNavigationWithAlert(performNavigation);
    } else {
      performNavigation();
    }
  }, [navigate, onNavigationWithAlert]);

  const handleTeamSelect = useCallback(
    (team: TeamConfig | null) => {
      loadPlans();
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
    [onTeamSelect, dispatchToast, loadPlans]
  );

  return (
    <div className="panel-left-container">
      <PanelLeft panelWidth={280} panelResize={true}>
        <PanelLeftToolbar
          linkTo={onNavigationWithAlert ? undefined : "/"}
          onTitleClick={onNavigationWithAlert ? handleLogoClick : undefined}
          panelTitle="Contoso"
          panelIcon={<ContosoLogo />}
        >
          <Tooltip content="New task" relationship={"label"} />
        </PanelLeftToolbar>

        {/* Team Selector right under the toolbar */}

        <div className="team-selector-container">
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
              selectedTeam={selectedTeam}
            />
          )}

        </div>
        <div
          className="tab tab-new-task"
          onClick={onNewTaskButton}
          tabIndex={0} // ✅ allows tab focus
          role="button" // ✅ announces as button
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onNewTaskButton();
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
          isLoadingTeam={isLoadingTeam}
        />

        <PanelFooter>
          <div className="panel-footer-content">
            {/* User Card */}
            <PanelUserCard
              name={userInfo?.user_first_last_name || "Guest"}
              size={32}
            />
          </div>
        </PanelFooter>
      </PanelLeft>
    </div>
  );
};

export default PlanPanelLeft;
