/**
 * App Slice — global application state: config, theme, WebSocket connection, auth.
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../store';
import { UserInfo } from '../../models';

export interface AppState {
    /** Has the runtime config been loaded from /config? */
    configLoaded: boolean;
    /** Is dark mode active? */
    isDarkMode: boolean;
    /** Is the global WebSocket connected? */
    wsConnected: boolean;
    /** Current user ID from EasyAuth */
    userId: string;
    /** Current user display name */
    userName: string;
    /** Current user email */
    userEmail: string;
}

const initialState: AppState = {
    configLoaded: false,
    isDarkMode: window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false,
    wsConnected: false,
    userId: '',
    userName: '',
    userEmail: '',
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
        hydrateCurrentUser(state, action: PayloadAction<UserInfo | null>) {
            const userInfo = action.payload;
            if (!userInfo || !userInfo.user_id) {
                state.userId = 'anonymous';
                state.userName = '';
                state.userEmail = '';
                return;
            }
            state.userId = userInfo.user_id || 'anonymous';
            state.userName = userInfo.user_first_last_name || '';
            // Extract email from claims
            const userClaims = userInfo.user_claims || [];
            let emailVal = userInfo.user_email || '';
            for (const claim of userClaims) {
                if (claim.typ === 'preferred_username' ||
                    claim.typ === 'email' ||
                    claim.typ === 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress' ||
                    claim.typ === 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn') {
                    emailVal = claim.val;
                    break;
                }
            }
            state.userEmail = emailVal;
        },
    },
});

export const {
    setConfigLoaded,
    setIsDarkMode,
    setWsConnected,
    hydrateCurrentUser,
} = appSlice.actions;

/* ── Granular Selectors ───────────────────────────────────────── */
export const selectConfigLoaded = (s: RootState) => s.app.configLoaded;
export const selectIsDarkMode = (s: RootState) => s.app.isDarkMode;
export const selectWsConnected = (s: RootState) => s.app.wsConnected;

export default appSlice.reducer;
