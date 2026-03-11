import React, { useEffect, useCallback } from 'react';
import { Spinner } from '@fluentui/react-components';
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
import InlineToaster, { useInlineToaster } from '../components/toast/InlineToaster';
import { useAppDispatch, useAppSelector } from '../state/hooks';
import {
    selectSelectedTeam,
    selectIsLoadingTeam,
    setSelectedTeam,
    setIsLoadingTeam,
} from '../state/slices/teamSlice';
import { selectReloadLeftList, setReloadLeftList } from '../state/slices/planSlice';

/**
 * HomePage component - displays task lists and provides navigation
 * Accessible via the route "/"
 */
const HomePage: React.FC = () => {
    const dispatch = useAppDispatch();
    const { showToast } = useInlineToaster();
    const selectedTeam = useAppSelector(selectSelectedTeam);
    const isLoadingTeam = useAppSelector(selectIsLoadingTeam);
    const reloadLeftList = useAppSelector(selectReloadLeftList);

    useEffect(() => {
        const initTeam = async () => {
            dispatch(setIsLoadingTeam(true));
            try {
                const initResponse = await TeamService.initializeTeam();

                if (initResponse.data?.status === 'Request started successfully' && initResponse.data?.team_id) {
                    const teams = await TeamService.getUserTeams();
                    const initializedTeam = teams.find(team => team.team_id === initResponse.data?.team_id);

                    if (initializedTeam) {
                        dispatch(setSelectedTeam(initializedTeam));
                        TeamService.storageTeam(initializedTeam);
                        showToast(
                            `${initializedTeam.name} team initialized successfully with ${initializedTeam.agents?.length || 0} agents`,
                            'success',
                        );
                    } else if (teams.length > 0) {
                        const defaultTeam = teams[0];
                        dispatch(setSelectedTeam(defaultTeam));
                        TeamService.storageTeam(defaultTeam);
                        showToast(`${defaultTeam.name} team loaded as default`, 'success');
                    }
                } else if (initResponse.data?.requires_team_upload) {
                    dispatch(setSelectedTeam(null));
                    showToast('Welcome! Please upload a team configuration file to get started.', 'info');
                } else if (!initResponse.success) {
                    // API call failed — surface the error
                    console.error('Team init failed:', initResponse.error);
                    showToast(initResponse.error || 'Team initialization failed. Please try again.', 'warning');
                }
            } catch (error) {
                console.error('Team initialization error:', error);
                showToast('Team initialization failed. You can still upload a custom team configuration.', 'info');
                dispatch(setSelectedTeam(null));
            } finally {
                dispatch(setIsLoadingTeam(false));
            }
        };

        initTeam();
    }, [dispatch]); // eslint-disable-line react-hooks/exhaustive-deps

    const handleNewTaskButton = useCallback(() => {
        NewTaskService.handleNewTaskFromHome();
    }, []);

    const handleTeamSelect = useCallback(
        async (team: TeamConfig | null) => {
            dispatch(setSelectedTeam(team));
            dispatch(setReloadLeftList(true));
            if (team) {
                try {
                    dispatch(setIsLoadingTeam(true));
                    const initResponse = await TeamService.initializeTeam(true);

                    if (initResponse.data?.status === 'Request started successfully' && initResponse.data?.team_id) {
                        const teams = await TeamService.getUserTeams();
                        const initializedTeam = teams.find(t => t.team_id === initResponse.data?.team_id);

                        if (initializedTeam) {
                            dispatch(setSelectedTeam(initializedTeam));
                            TeamService.storageTeam(initializedTeam);
                            dispatch(setReloadLeftList(true));
                            showToast(
                                `${initializedTeam.name} team initialized successfully with ${initializedTeam.agents?.length || 0} agents`,
                                'success',
                            );
                        }
                    } else if (initResponse.data?.requires_team_upload) {
                        dispatch(setSelectedTeam(null));
                        showToast('No teams are configured. Please upload a team configuration to continue.', 'info');
                    } else {
                        throw new Error('Invalid response from init_team endpoint');
                    }
                } catch {
                    showToast('Error switching team. Please try again.', 'warning');
                } finally {
                    dispatch(setIsLoadingTeam(false));
                }
            } else {
                showToast('No team is currently selected', 'info');
            }
        },
        [dispatch, showToast],
    );

    const handleTeamUpload = useCallback(async () => {
        try {
            const teams = await TeamService.getUserTeams();
            if (teams.length > 0) {
                const hrTeam = teams.find(team => team.name === 'Human Resources Team');
                const defaultTeam = hrTeam || teams[0];
                dispatch(setSelectedTeam(defaultTeam));
                showToast(`Team uploaded successfully! ${defaultTeam.name} remains your default team.`, 'success');
            }
        } catch {
            console.error('Team upload failed');
        }
    }, [dispatch, showToast]);

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
                        <ContentToolbar panelTitle="Multi-Agent Planner" />
                        {!isLoadingTeam ? (
                            <HomeInput selectedTeam={selectedTeam} />
                        ) : (
                            <div
                                style={{
                                    display: 'flex',
                                    justifyContent: 'center',
                                    alignItems: 'center',
                                    height: '200px',
                                }}
                            >
                                <Spinner label="Loading team configuration..." />
                            </div>
                        )}
                    </Content>
                </CoralShellRow>
            </CoralShellColumn>
        </>
    );
};

const MemoizedHomePage = React.memo(HomePage);
MemoizedHomePage.displayName = 'HomePage';
export default MemoizedHomePage;