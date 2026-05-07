/**
 * App Slice — global application state: config, theme, WebSocket connection, auth.
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../store';

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

type AuthClaim = { typ: string; val: string };
type AuthPayload = Array<{ user_id: string; user_claims: AuthClaim[] }>;

export const fetchCurrentUser = createAsyncThunk(
    'app/fetchCurrentUser',
    async () => {
        try {
            const response = await fetch('/.auth/me');
            if (!response.ok) {
                return { userId: 'anonymous', userName: '', userEmail: '' };
            }
            const payload: AuthPayload = await response.json();

            const userClaims = payload[0]?.user_claims || [];
            const objectIdClaim = userClaims.find(
                (claim) =>
                    claim.typ === 'http://schemas.microsoft.com/identity/claims/objectidentifier'
            );
            const nameClaim = userClaims.find(
                (claim) => claim.typ === 'name'
            );

            let emailVal = '';
            for (const claim of userClaims) {
                if (claim.typ === 'preferred_username' ||
                    claim.typ === 'email' ||
                    claim.typ === 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress' ||
                    claim.typ === 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn') {
                    emailVal = claim.val;
                    break;
                }
            }

            return {
                userId: objectIdClaim?.val || payload[0]?.user_id || 'anonymous',
                userName: nameClaim?.val || '',
                userEmail: emailVal,
            };
        } catch {
            return { userId: 'anonymous', userName: '', userEmail: '' };
        }
    }
);

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
    extraReducers: (builder) => {
        builder
            .addCase(fetchCurrentUser.fulfilled, (state, action) => {
                state.userId = action.payload.userId;
                state.userName = action.payload.userName;
                state.userEmail = action.payload.userEmail;
            })
            .addCase(fetchCurrentUser.rejected, (state) => {
                state.userId = 'anonymous';
                state.userName = '';
                state.userEmail = '';
            });
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
