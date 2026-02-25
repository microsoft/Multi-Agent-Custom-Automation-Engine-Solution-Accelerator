import React, { useCallback } from 'react';
import {
    Spinner
} from '@fluentui/react-components';
import '../styles/PlanPage.css';
import CoralShellColumn from '../coral/components/Layout/CoralShellColumn';
import CoralShellRow from '../coral/components/Layout/CoralShellRow';
import Content from '../coral/components/Content/Content';
import HomeInput from '@/components/content/HomeInput';
import { NewTaskService } from '../services/NewTaskService';
import PlanPanelLeft from '@/components/content/PlanPanelLeft';
import ContentToolbar from '@/coral/components/Content/ContentToolbar';
import { TeamConfig } from '../models/Team';
import InlineToaster, { useInlineToaster } from "../components/toast/InlineToaster";
import { useTeamInit } from '../hooks/useTeamInit';
import {
    useAppDispatch,
    useAppSelector,
    selectReloadLeftList,
    triggerReloadLeftList,
} from '../store';

/**
 * HomePage component - displays task lists and provides navigation
 * Accessible via the route "/"
 */
const HomePage: React.FC = () => {
    const { showToast } = useInlineToaster();
    const dispatch = useAppDispatch();
    const reloadLeftList = useAppSelector(selectReloadLeftList);

    // ── Team initialization hook ──
    const {
        selectedTeam,
        isLoadingTeam,
        setSelectedTeamValue,
        reinitializeTeam,
    } = useTeamInit(showToast);

    /**
    * Handle new task creation from the "New task" button
    * Resets textarea to empty state on HomePage
    */
    const handleNewTaskButton = useCallback(() => {
        NewTaskService.handleNewTaskFromHome();
    }, []);

    /**
     * Handle team selection from the Settings button
     */
    const handleTeamSelect = useCallback(async (team: TeamConfig | null) => {
        setSelectedTeamValue(team);
        dispatch(triggerReloadLeftList());

        if (team) {
            try {
                await reinitializeTeam(true);
                showToast(
                    `${team.name} team has been selected with ${team.agents.length} agents`,
                    "success"
                );
            } catch (error) {
                console.error('Error setting current team:', error);
                showToast("Error switching team. Please try again.", "warning");
            }
        } else {
            showToast("No team is currently selected", "info");
        }
    }, [showToast, dispatch, setSelectedTeamValue, reinitializeTeam]);


    /**
     * Handle team upload completion - re-initialize team to pick up newly uploaded config
     */
    const handleTeamUpload = useCallback(async () => {
        try {
            await reinitializeTeam(true);
            showToast("Team uploaded successfully!", "success");
        } catch (error) {
            console.error('Error refreshing teams after upload:', error);
        }
    }, [showToast, reinitializeTeam]);


    return (
        <>
            <InlineToaster />
            <CoralShellColumn>
                <CoralShellRow>
                    <PlanPanelLeft
                        reloadTasks={reloadLeftList}
                        onNewTaskButton={handleNewTaskButton}
                        onTeamSelect={handleTeamSelect}
                        onTeamUpload={handleTeamUpload}
                        isHomePage={true}
                        selectedTeam={selectedTeam}
                        isLoadingTeam={isLoadingTeam}
                    />
                    <Content>
                        <ContentToolbar
                            panelTitle={"Multi-Agent Planner"}
                        ></ContentToolbar>
                        {!isLoadingTeam ? (
                            <HomeInput
                                selectedTeam={selectedTeam}
                            />
                        ) : (
                            <div style={{
                                display: 'flex',
                                justifyContent: 'center',
                                alignItems: 'center',
                                height: '200px'
                            }}>
                                <Spinner label="Loading team configuration..." />
                            </div>
                        )}
                    </Content>

                </CoralShellRow>
            </CoralShellColumn>
        </>
    );
};

export default HomePage;