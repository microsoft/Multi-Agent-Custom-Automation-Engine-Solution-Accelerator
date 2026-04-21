/**
 * App Slice — global application state: config, theme, WebSocket connection.
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../store';

export interface AppState {
    /** Has the runtime config been loaded from /config? */
    configLoaded: boolean;
    /** Is dark mode active? */
    isDarkMode: boolean;
    /** Is the global WebSocket connected? */
    wsConnected: boolean;
}

const initialState: AppState = {
    configLoaded: false,
    isDarkMode: window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false,
    wsConnected: false,
};

const appSlice = createSlice({
    name: 'app',
    initialState,
    reducers: {
        setConfigLoaded(state, action: PayloadAction<boolean>) {
            state.configLoaded = action.payload;
        },
        setIsDarkMode(state, action: PayloadAction<boolean>) {
            state.isDarkMode = action.payload;
        },
        setWsConnected(state, action: PayloadAction<boolean>) {
            state.wsConnected = action.payload;
        },
    },
});

export const {
    setConfigLoaded,
    setIsDarkMode,
    setWsConnected,
} = appSlice.actions;

/* ── Granular Selectors ───────────────────────────────────────── */
export const selectConfigLoaded = (s: RootState) => s.app.configLoaded;
export const selectIsDarkMode = (s: RootState) => s.app.isDarkMode;
export const selectWsConnected = (s: RootState) => s.app.wsConnected;

export default appSlice.reducer;
