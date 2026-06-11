import { TeamConfig } from "@/models";
import { Body1, Caption1 } from "@fluentui/react-components";
import styles from '../../styles/TeamSelector.module.css';
export interface TeamSelectedProps {
    selectedTeam?: TeamConfig | null;
}

const TeamSelected: React.FC<TeamSelectedProps> = ({ selectedTeam }) => {
    return (
        <div className={styles.teamSelectorContent}>
            <Caption1 className={styles.currentTeamLabel}>
                &nbsp;&nbsp;Current Team
            </Caption1>
            <Body1 className={styles.currentTeamName}>
                &nbsp;&nbsp;{selectedTeam ? selectedTeam.name : 'No team selected'}
            </Body1>
        </div>
    );
}
export default TeamSelected;