import { createSlice, PayloadAction } from '@reduxjs/toolkit';

/**
 * Represents a task item in the chat history sidebar
 */
export interface TaskHistoryItem {
    id: string;
    title: string;
    status: string;
    timestamp: string;
    teamId?: string;
}

/**
 * Chat History slice - handles sidebar task history state
 */
export interface ChatHistoryState {
    /** Whether to reload the left task list */
    reloadLeftList: boolean;
    /** List of tasks for left panel */
    taskHistory: TaskHistoryItem[];
    /** Selected task ID in the sidebar */
    selectedTaskId: string | null;
    /** Whether task history is loading */
    isLoadingHistory: boolean;
}

const initialState: ChatHistoryState = {
    reloadLeftList: true,
    taskHistory: [],
    selectedTaskId: null,
    isLoadingHistory: false,
};

const chatHistorySlice = createSlice({
    name: 'chatHistory',
    initialState,
    reducers: {
        setReloadLeftList: (state, action: PayloadAction<boolean>) => {
            state.reloadLeftList = action.payload;
        },
        triggerReloadLeftList: (state) => {
            state.reloadLeftList = true;
        },
        clearReloadLeftList: (state) => {
            state.reloadLeftList = false;
        },
        setTaskHistory: (state, action: PayloadAction<TaskHistoryItem[]>) => {
            state.taskHistory = action.payload;
        },
        addTaskToHistory: (state, action: PayloadAction<TaskHistoryItem>) => {
            // Add to beginning of list (most recent first)
            state.taskHistory.unshift(action.payload);
        },
        updateTaskInHistory: (state, action: PayloadAction<{ id: string; updates: Partial<TaskHistoryItem> }>) => {
            const index = state.taskHistory.findIndex(task => task.id === action.payload.id);
            if (index !== -1) {
                state.taskHistory[index] = { ...state.taskHistory[index], ...action.payload.updates };
            }
        },
        removeTaskFromHistory: (state, action: PayloadAction<string>) => {
            state.taskHistory = state.taskHistory.filter(task => task.id !== action.payload);
        },
        setSelectedTaskId: (state, action: PayloadAction<string | null>) => {
            state.selectedTaskId = action.payload;
        },
        setIsLoadingHistory: (state, action: PayloadAction<boolean>) => {
            state.isLoadingHistory = action.payload;
        },
        /**
         * Reset chat history state to initial values
         */
        resetChatHistoryState: () => initialState,
    },
});

export const {
    setReloadLeftList,
    triggerReloadLeftList,
    clearReloadLeftList,
    setTaskHistory,
    addTaskToHistory,
    updateTaskInHistory,
    removeTaskFromHistory,
    setSelectedTaskId,
    setIsLoadingHistory,
    resetChatHistoryState,
} = chatHistorySlice.actions;

export default chatHistorySlice.reducer;
