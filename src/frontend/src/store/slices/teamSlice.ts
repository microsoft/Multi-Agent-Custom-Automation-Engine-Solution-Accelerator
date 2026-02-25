import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { TeamConfig } from '../../models';
import { TeamService } from '../../services/TeamService';

/**
 * Team slice - handles team-related state
 */
export interface TeamState {
    /** Currently selected team */
    selectedTeam: TeamConfig | null;
    /** List of available teams */
    teams: TeamConfig[];
    /** Whether team is loading */
    isLoadingTeam: boolean;
    /** Error message for team operations */
    teamError: string | null;
    /** Whether team requires upload */
    requiresTeamUpload: boolean;
}

const initialState: TeamState = {
    selectedTeam: null,
    teams: [],
    isLoadingTeam: true,
    teamError: null,
    requiresTeamUpload: false,
};

/**
 * Async thunk to initialize team from backend
 */
export const initializeTeam = createAsyncThunk(
    'team/initializeTeam',
    async (forceReload: boolean = false, { rejectWithValue }) => {
        try {
            const initResponse = await TeamService.initializeTeam(forceReload);
            
            if (initResponse.data?.status === 'Request started successfully' && initResponse.data?.team_id) {
                // Fetch the actual team details using the team_id
                const teams = await TeamService.getUserTeams();
                const initializedTeam = teams.find(team => team.team_id === initResponse.data?.team_id);
                
                return {
                    team: initializedTeam || teams[0] || null,
                    teams,
                    requiresUpload: false,
                };
            } else if (initResponse.data?.requires_team_upload) {
                return {
                    team: null,
                    teams: [],
                    requiresUpload: true,
                };
            }
            
            throw new Error('Invalid response from init_team endpoint');
        } catch (error: any) {
            return rejectWithValue(error.message || 'Failed to initialize team');
        }
    }
);

/**
 * Async thunk to fetch user teams
 */
export const fetchUserTeams = createAsyncThunk(
    'team/fetchUserTeams',
    async (_, { rejectWithValue }) => {
        try {
            const teams = await TeamService.getUserTeams();
            return teams;
        } catch (error: any) {
            return rejectWithValue(error.message || 'Failed to fetch teams');
        }
    }
);

const teamSlice = createSlice({
    name: 'team',
    initialState,
    reducers: {
        setSelectedTeam: (state, action: PayloadAction<TeamConfig | null>) => {
            state.selectedTeam = action.payload;
            if (action.payload) {
                TeamService.storageTeam(action.payload);
            }
        },
        setTeams: (state, action: PayloadAction<TeamConfig[]>) => {
            state.teams = action.payload;
        },
        setIsLoadingTeam: (state, action: PayloadAction<boolean>) => {
            state.isLoadingTeam = action.payload;
        },
        setTeamError: (state, action: PayloadAction<string | null>) => {
            state.teamError = action.payload;
        },
        setRequiresTeamUpload: (state, action: PayloadAction<boolean>) => {
            state.requiresTeamUpload = action.payload;
        },
        /**
         * Reset team state to initial values
         */
        resetTeamState: () => initialState,
    },
    extraReducers: (builder) => {
        builder
            // initializeTeam
            .addCase(initializeTeam.pending, (state) => {
                state.isLoadingTeam = true;
                state.teamError = null;
            })
            .addCase(initializeTeam.fulfilled, (state, action) => {
                state.isLoadingTeam = false;
                state.selectedTeam = action.payload.team;
                state.teams = action.payload.teams;
                state.requiresTeamUpload = action.payload.requiresUpload;
                if (action.payload.team) {
                    TeamService.storageTeam(action.payload.team);
                }
            })
            .addCase(initializeTeam.rejected, (state, action) => {
                state.isLoadingTeam = false;
                state.teamError = action.payload as string;
            })
            // fetchUserTeams
            .addCase(fetchUserTeams.pending, (state) => {
                state.isLoadingTeam = true;
            })
            .addCase(fetchUserTeams.fulfilled, (state, action) => {
                state.isLoadingTeam = false;
                state.teams = action.payload;
            })
            .addCase(fetchUserTeams.rejected, (state, action) => {
                state.isLoadingTeam = false;
                state.teamError = action.payload as string;
            });
    },
});

export const {
    setSelectedTeam,
    setTeams,
    setIsLoadingTeam,
    setTeamError,
    setRequiresTeamUpload,
    resetTeamState,
} = teamSlice.actions;

export default teamSlice.reducer;
