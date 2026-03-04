/**
 * Team Slice — selected team and loading state.
 */
import { createSlice, createSelector, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../store';
import { TeamConfig } from '@/models/Team';

export interface TeamState {
    /** Currently selected team */
    selectedTeam: TeamConfig | null;
    /** Is the team being loaded / initialised? */
    isLoadingTeam: boolean;
}

const initialState: TeamState = {
    selectedTeam: null,
    isLoadingTeam: true,
};

const teamSlice = createSlice({
    name: 'team',
    initialState,
    reducers: {
        setSelectedTeam(state, action: PayloadAction<TeamConfig | null>) {
            state.selectedTeam = action.payload as any;
        },
        setIsLoadingTeam(state, action: PayloadAction<boolean>) {
            state.isLoadingTeam = action.payload;
        },
        resetTeam() {
            return { ...initialState };
        },
    },
});

export const {
    setSelectedTeam,
    setIsLoadingTeam,
    resetTeam,
} = teamSlice.actions;

/* ── Granular Selectors ───────────────────────────────────────── */
export const selectSelectedTeam = (s: RootState) => s.team.selectedTeam;
export const selectIsLoadingTeam = (s: RootState) => s.team.isLoadingTeam;

/* ── Memoized Derived Selectors ───────────────────────────────── */

/** Team name (primitive — prevents child re-renders when other team fields change) */
export const selectTeamName = createSelector(
    selectSelectedTeam,
    (team) => team?.name ?? null,
);

/** Number of agents in the selected team */
export const selectTeamAgentCount = createSelector(
    selectSelectedTeam,
    (team) => team?.agents?.length ?? 0,
);

export default teamSlice.reducer;
