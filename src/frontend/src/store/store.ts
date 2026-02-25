import { configureStore } from '@reduxjs/toolkit';
import appReducer from './slices/appSlice';
import chatReducer from './slices/chatSlice';
import planReducer from './slices/planSlice';
import teamReducer from './slices/teamSlice';
import chatHistoryReducer from './slices/chatHistorySlice';
import citationReducer from './slices/citationSlice';

/**
 * Configure the Redux store with all domain-specific slices
 */
export const store = configureStore({
    reducer: {
        app: appReducer,
        chat: chatReducer,
        plan: planReducer,
        team: teamReducer,
        chatHistory: chatHistoryReducer,
        citation: citationReducer,
    },
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({
            // Allow non-serializable values for complex objects like refs, dates, etc.
            serializableCheck: {
                ignoredActions: ['plan/setPlanData', 'plan/setPlanApprovalRequest'],
                ignoredPaths: ['plan.planData', 'plan.planApprovalRequest'],
            },
        }),
    devTools: process.env.NODE_ENV !== 'production',
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export default store;
