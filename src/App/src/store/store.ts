/**
 * Redux Store Configuration
 *
 * Single source of truth for all application state.
 * Uses Redux Toolkit's configureStore with typed hooks.
 */
import { configureStore } from '@reduxjs/toolkit';
import planReducer from './slices/planSlice';
import chatReducer from './slices/chatSlice';
import appReducer from './slices/appSlice';
import teamReducer from './slices/teamSlice';
import streamingReducer from './slices/streamingSlice';

export const store = configureStore({
    reducer: {
        plan: planReducer,
        chat: chatReducer,
        app: appReducer,
        team: teamReducer,
        streaming: streamingReducer,
    },
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({
            serializableCheck: {
                // Ignore non-serializable values in specific paths
                ignoredActions: [
                    'plan/setPlanData',
                    'streaming/addStreamingMessage',
                    'chat/setMessagesContainerRef',
                ],
                ignoredPaths: [
                    'plan.planData.raw_data',
                    'streaming.streamingMessages',
                    'chat.messagesContainerRef',
                ],
            },
        }),
    devTools: import.meta.env.DEV,
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
