import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { TeamService } from '../services/TeamService';
import InlineToaster, { useInlineToaster } from "../components/toast/InlineToaster";

/**
 * HomePage component - displays task lists and provides navigation
 * Accessible via the route "/"
 */
const HomePage: React.FC = () => {
    const navigate = useNavigate();
    const { showToast, dismissToast } = useInlineToaster();
    const [selectedTeam, setSelectedTeam] = useState<TeamConfig | null>(null);
    const [isLoadingTeam, setIsLoadingTeam] = useState<boolean>(true);
    const [reloadLeftList, setReloadLeftList] = useState<boolean>(true);

    useEffect(() => {
        const initTeam = async () => {
            setIsLoadingTeam(true);

            try {
                console.log('Initializing team from backend...');
                // Call the backend init_team endpoint (takes ~20 seconds)
                const initResponse = await TeamService.initializeTeam();

                if (initResponse.data?.status === 'Request started successfully' && initResponse.data?.team_id) {
                    console.log('Team initialization completed:', initResponse.data?.team_id);

                    // Now fetch the actual team details using the team_id
                    const teams = await TeamService.getUserTeams();
                    const initializedTeam = teams.find(team => team.team_id === initResponse.data?.team_id);

                    if (initializedTeam) {
                        setSelectedTeam(initializedTeam);
                        TeamService.storageTeam(initializedTeam);

                        console.log('Team loaded successfully:', initializedTeam.name);
                        console.log('Team agents:', initializedTeam.agents?.length || 0);

                        showToast(
                            `${initializedTeam.name} team initialized successfully with ${initializedTeam.agents?.length || 0} agents`,
                            "success"
                        );
                    } else {
                        // Fallback: if we can't find the specific team, use HR team or first available
                        console.log('Specific team not found, using default selection logic');
                        const hrTeam = teams.find(team => team.name === "Human Resources Team");
                        const defaultTeam = hrTeam || teams[0];

                        if (defaultTeam) {
                            setSelectedTeam(defaultTeam);
                            TeamService.storageTeam(defaultTeam);
                            showToast(
                                `${defaultTeam.name} team loaded as default`,
                                "success"
                            );
                        }
                    }

                }

            } catch (error) {
                console.error('Error initializing team from backend:', error);
                showToast("Team initialization failed", "warning");

                // Fallback to the old client-side method

            } finally {
                setIsLoadingTeam(false);
            }
        };

        initTeam();
    }, []);

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
        setSelectedTeam(team);
        setReloadLeftList(true);
        console.log('handleTeamSelect called with team:', true);
        if (team) {

            try {
                setIsLoadingTeam(true);
                const initResponse = await TeamService.initializeTeam(true);

                if (initResponse.data?.status === 'Request started successfully' && initResponse.data?.team_id) {
                    console.log('handleTeamSelect:', initResponse.data?.team_id);

                    // Now fetch the actual team details using the team_id
                    const teams = await TeamService.getUserTeams();
                    const initializedTeam = teams.find(team => team.team_id === initResponse.data?.team_id);

                    if (initializedTeam) {
                        setSelectedTeam(initializedTeam);
                        TeamService.storageTeam(initializedTeam);
                        setReloadLeftList(true)
                        console.log('Team loaded successfully handleTeamSelect:', initializedTeam.name);
                        console.log('Team agents handleTeamSelect:', initializedTeam.agents?.length || 0);

                        showToast(
                            `${initializedTeam.name} team initialized successfully with ${initializedTeam.agents?.length || 0} agents`,
                            "success"
                        );
                    }

                } else {
                    throw new Error('Invalid response from init_team endpoint');
                }
            } catch (error) {
                console.error('Error setting current team:', error);
            } finally {
                setIsLoadingTeam(false);
            }


            showToast(
                `${team.name} team has been selected with ${team.agents.length} agents`,
                "success"
            );
        } else {
            showToast(
                "No team is currently selected",
                "info"
            );
        }
    }, [showToast, setReloadLeftList]);


    /**
     * Handle team upload completion - refresh team list and keep Business Operations Team as default
     */
    const handleTeamUpload = useCallback(async () => {
        try {
            const teams = await TeamService.getUserTeams();
            console.log('Teams refreshed after upload:', teams.length);

            if (teams.length > 0) {
                // Always keep "Human Resources Team" as default, even after new uploads
                const hrTeam = teams.find(team => team.name === "Human Resources Team");
                const defaultTeam = hrTeam || teams[0];
                setSelectedTeam(defaultTeam);
                console.log('Default team after upload:', defaultTeam.name);
                console.log('Human Resources Team remains default');
                showToast(
                    `Team uploaded successfully! ${defaultTeam.name} remains your default team.`,
                    "success"
                );
            }
        } catch (error) {
            console.error('Error refreshing teams after upload:', error);
        }
    }, [showToast]);


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