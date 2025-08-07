import { TeamConfig } from './Team';

export interface PlanPanelLefProps {
    reloadTasks?: boolean;
    onNewTaskButton: () => void;
    restReload?: () => void;
    onTeamSelect?: (team: TeamConfig) => void;
    onTeamUpload?: () => Promise<void>;
    selectedTeam?: TeamConfig | null;
}