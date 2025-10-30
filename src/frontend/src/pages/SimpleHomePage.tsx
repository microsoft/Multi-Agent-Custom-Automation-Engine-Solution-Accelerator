import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Spinner
} from '@fluentui/react-components';
import '../styles/SimplePage.css';
import CoralShellColumn from '../coral/components/Layout/CoralShellColumn';
import CoralShellRow from '../coral/components/Layout/CoralShellRow';
import Content from '../coral/components/Content/Content';
import { NewTaskService } from '../services/NewTaskService';
import PlanPanelLeft from '@/components/content/PlanPanelLeft';
import ContentToolbar from '@/coral/components/Content/ContentToolbar';
import ForecastDatasetPanel from '@/components/content/ForecastDatasetPanel';
import { TeamConfig } from '../models/Team';
import { TeamService } from '../services/TeamService';
import InlineToaster, { useInlineToaster } from "../components/toast/InlineToaster";
import SimpleInput from '@/components/content/SimpleInput';

/**
 * SimpleHomePage component - Simplified user-friendly interface
 * Accessible via the route "/"
 */
const SimpleHomePage: React.FC = () => {
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
                const initResponse = await TeamService.initializeTeam();

                if (initResponse.data?.status === 'Request started successfully' && initResponse.data?.team_id) {
                    console.log('Team initialization completed:', initResponse.data?.team_id);

                    const teams = await TeamService.getUserTeams();
                    const initializedTeam = teams.find(team => team.team_id === initResponse.data?.team_id);

                    if (initializedTeam) {
                        setSelectedTeam(initializedTeam);
                        TeamService.storageTeam(initializedTeam);

                        console.log('Team loaded successfully:', initializedTeam.name);
                        showToast(
                            `${initializedTeam.name} ready with ${initializedTeam.agents?.length || 0} agents`,
                            "success"
                        );
                    } else {
                        const hrTeam = teams.find(team => team.name === "Human Resources Team");
                        const defaultTeam = hrTeam || teams[0];

                        if (defaultTeam) {
                            setSelectedTeam(defaultTeam);
                            TeamService.storageTeam(defaultTeam);
                            showToast(
                                `${defaultTeam.name} loaded`,
                                "success"
                            );
                        }
                    }
                }
            } catch (error) {
                console.error('Error initializing team from backend:', error);
                showToast("Team initialization failed", "warning");
            } finally {
                setIsLoadingTeam(false);
            }
        };

        initTeam();
    }, []);

    const handleNewTaskButton = useCallback(() => {
        NewTaskService.handleNewTaskFromHome();
    }, []);

    const handleTeamSelect = useCallback(async (team: TeamConfig | null) => {
        setSelectedTeam(team);
        setReloadLeftList(true);
        
        if (team) {
            try {
                setIsLoadingTeam(true);
                const initResponse = await TeamService.initializeTeam(true);

                if (initResponse.data?.status === 'Request started successfully' && initResponse.data?.team_id) {
                    const teams = await TeamService.getUserTeams();
                    const initializedTeam = teams.find(team => team.team_id === initResponse.data?.team_id);

                    if (initializedTeam) {
                        setSelectedTeam(initializedTeam);
                        TeamService.storageTeam(initializedTeam);
                        setReloadLeftList(true);
                        
                        showToast(
                            `${initializedTeam.name} ready with ${initializedTeam.agents?.length || 0} agents`,
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
                `${team.name} selected`,
                "success"
            );
        }
    }, [showToast, setReloadLeftList]);

    const handleTeamUpload = useCallback(async () => {
        try {
            const teams = await TeamService.getUserTeams();
            console.log('Teams refreshed after upload:', teams.length);

            if (teams.length > 0) {
                const hrTeam = teams.find(team => team.name === "Human Resources Team");
                const defaultTeam = hrTeam || teams[0];
                setSelectedTeam(defaultTeam);
                showToast(
                    `Team uploaded successfully! ${defaultTeam.name} is now active.`,
                    "success"
                );
            }
        } catch (error) {
            console.error('Error refreshing teams after upload:', error);
        }
    }, [showToast]);

    const resetReload = useCallback(() => {
        setReloadLeftList(false);
    }, []);

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
                        restReload={resetReload}
                    />
                    <Content>
                        <ContentToolbar
                            panelTitle={"AI Assistant"}
                        ></ContentToolbar>
                        <ForecastDatasetPanel />
                        {!isLoadingTeam ? (
                            <SimpleInput
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

export default SimpleHomePage;











