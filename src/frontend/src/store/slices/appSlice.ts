import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { loadingMessages } from '../../coral/components/LoadingMessage';

/**
 * App slice - handles global application state
 */
export interface AppState {
    /** Whether the app config is loaded */
    isConfigLoaded: boolean;
    /** Whether user info is loaded */
    isUserInfoLoaded: boolean;
    /** Whether dark mode is enabled */
    isDarkMode: boolean;
    /** WebSocket connection status */
    wsConnected: boolean;
    /** Current loading message to display */
    loadingMessage: string;
    /** Global loading state */
    isLoading: boolean;
    /** Global error message */
    errorMessage: string | null;
}

const initialState: AppState = {
    isConfigLoaded: false,
    isUserInfoLoaded: false,
    isDarkMode: window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false,
    wsConnected: false,
    loadingMessage: loadingMessages[0],
    isLoading: false,
    errorMessage: null,
};

const appSlice = createSlice({
    name: 'app',
    initialState,
    reducers: {
        setConfigLoaded: (state, action: PayloadAction<boolean>) => {
            state.isConfigLoaded = action.payload;
        },
        setUserInfoLoaded: (state, action: PayloadAction<boolean>) => {
            state.isUserInfoLoaded = action.payload;
        },
        setDarkMode: (state, action: PayloadAction<boolean>) => {
            state.isDarkMode = action.payload;
        },
        setWsConnected: (state, action: PayloadAction<boolean>) => {
            state.wsConnected = action.payload;
        },
        setLoadingMessage: (state, action: PayloadAction<string>) => {
            state.loadingMessage = action.payload;
        },
        setIsLoading: (state, action: PayloadAction<boolean>) => {
            state.isLoading = action.payload;
        },
        setErrorMessage: (state, action: PayloadAction<string | null>) => {
            state.errorMessage = action.payload;
        },
        /**
         * Rotate to the next loading message
         */
        rotateLoadingMessage: (state) => {
            const currentIndex = loadingMessages.indexOf(state.loadingMessage);
            const nextIndex = (currentIndex + 1) % loadingMessages.length;
            state.loadingMessage = loadingMessages[nextIndex];
        },
        /**
         * Reset app state to initial values
         */
        resetAppState: () => initialState,
    },
});

export const {
    setConfigLoaded,
    setUserInfoLoaded,
    setDarkMode,
    setWsConnected,
    setLoadingMessage,
    setIsLoading,
    setErrorMessage,
    rotateLoadingMessage,
    resetAppState,
} = appSlice.actions;

export default appSlice.reducer;
