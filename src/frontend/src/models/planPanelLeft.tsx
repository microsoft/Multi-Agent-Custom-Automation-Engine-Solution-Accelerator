import { TeamConfig } from './Team';

export interface PlanPanelLefProps {
    reloadTasks: boolean;
    onNewTaskButton: () => void;
    restReload?: () => void;
    onTeamSelect?: (team: TeamConfig | null) => void;
    onTeamUpload?: () => Promise<void>;
    isHomePage: boolean;
    selectedTeam?: TeamConfig | null;
    onNavigationWithAlert?: (navigationFn: () => void) => void;
}