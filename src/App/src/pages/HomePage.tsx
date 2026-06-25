import React, { useEffect, useCallback } from 'react';
import { Spinner } from '@fluentui/react-components';
import '../styles/PlanPage.css';
import CoralShellColumn from '../commonComponents/components/Layout/CoralShellColumn';
import CoralShellRow from '../commonComponents/components/Layout/CoralShellRow';
import Content from '../commonComponents/components/Content/Content';
import HomeInput from '@/components/content/HomeInput';
import { NewTaskService } from '../store/NewTaskService';
import PlanPanelLeft from '@/components/content/PlanPanelLeft';
import ContentToolbar from '@/commonComponents/components/Content/ContentToolbar';
import { TeamConfig } from '../models/Team';
import { TeamService } from '../store/TeamService';
import InlineToaster, { useInlineToaster } from '../components/toast/InlineToaster';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
    selectSelectedTeam,
    selectIsLoadingTeam,
    setSelectedTeam,
    setIsLoadingTeam,
} from '../store/slices/teamSlice';
import { selectReloadLeftList, setReloadLeftList } from '../store/slices/planSlice';

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
                // Get available teams first
                const teams = await TeamService.getUserTeams();
                
                // Check if we have a stored team and if it still exists in the backend
                const storedTeam = TeamService.getStoredTeam();
                if (storedTeam) {
                    const existsInBackend = teams.some(t => t.team_id === storedTeam.team_id);
                    if (existsInBackend) {
                        // Stored team still exists, use it
                        dispatch(setSelectedTeam(storedTeam));
                        showToast(`${storedTeam.name} team restored from storage`, 'success');
                        dispatch(setIsLoadingTeam(false));
                        return;
                    } else {
                        // Stored team was deleted, clear localStorage
                        console.warn(`Stored team ${storedTeam.team_id} no longer exists, clearing storage`);
                        // Don't call storageTeam with null, just let init response guide us
                    }
                }

                // Now initialize team from backend
                const initResponse = await TeamService.initializeTeam();

                if (initResponse.data?.status === 'Request started successfully' && initResponse.data?.team_id) {
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
            
            // Immediately save selected team to localStorage so it persists on reload
            if (team) {
                TeamService.storageTeam(team);
            }
            
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

    const handleTeamUpload = useCallback(async (uploadedTeam?: any) => {
        try {
            console.log('handleTeamUpload called with:', uploadedTeam);
            if (uploadedTeam) {
                const teamName = uploadedTeam.name || 'Uploaded Team';
                dispatch(setSelectedTeam(uploadedTeam));
                TeamService.storageTeam(uploadedTeam);
                showToast(`Default team set to ${teamName}`, 'success');

                // Also inform backend to use this team for the session
                if (uploadedTeam.team_id) {
                    try {
                        await TeamService.selectTeam(uploadedTeam.team_id);
                        console.log('Team selected in backend:', uploadedTeam.team_id);
                    } catch (selectError) {
                        console.warn('Failed to select team in backend:', selectError);
                        // Don't fail the upload if backend selection fails
                    }
                }
            } else {
                console.warn('No uploaded team provided to handleTeamUpload');
            }
        } catch (error) {
            console.error('Team upload failed:', error);
            showToast('Team upload completed', 'success');
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