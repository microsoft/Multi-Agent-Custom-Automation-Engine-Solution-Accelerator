import { TeamConfig } from './Team';

export interface PlanPanelLefProps {
    reloadTasks?: boolean;
    onNewTaskButton: () => void;
    restReload?: () => void;
    onTeamSelect?: (team: TeamConfig | null) => void;
    onTeamUpload?: () => Promise<void>;
    selectedTeam?: TeamConfig | null;
}