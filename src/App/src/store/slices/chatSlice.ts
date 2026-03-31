/**
 * Chat Slice — user input, submission state, agent messages,
 * and clarification handling.
 */
import { createSlice, createSelector, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../store';
import { AgentMessageData, ParsedUserClarification } from '@/models';

export interface ChatState {
    /** Current chat input value */
    input: string;
    /** Disable the input while a submission is in flight */
    submittingChatDisableInput: boolean;
    /** Clarification request from the backend */
    clarificationMessage: ParsedUserClarification | null;
    /** All agent messages rendered in the chat panel */
    agentMessages: AgentMessageData[];
}

const initialState: ChatState = {
    input: '',
    submittingChatDisableInput: true,
    clarificationMessage: null,
    agentMessages: [],
};

const chatSlice = createSlice({
    name: 'chat',
    initialState,
    reducers: {
        setInput(state, action: PayloadAction<string>) {
            state.input = action.payload;
        },
        setSubmittingChatDisableInput(state, action: PayloadAction<boolean>) {
            state.submittingChatDisableInput = action.payload;
        },
        setClarificationMessage(state, action: PayloadAction<ParsedUserClarification | null>) {
            state.clarificationMessage = action.payload as any;
        },
        setAgentMessages(state, action: PayloadAction<AgentMessageData[]>) {
            state.agentMessages = action.payload as any;
        },
        addAgentMessage(state, action: PayloadAction<AgentMessageData>) {
            state.agentMessages.push(action.payload as any);
        },
        /** Reset chat state (used when navigating to a new plan) */
        resetChat() {
            return { ...initialState };
        },
    },
});

export const {
    setInput,
    setSubmittingChatDisableInput,
    setClarificationMessage,
    setAgentMessages,
    addAgentMessage,
    resetChat,
} = chatSlice.actions;

/* ── Granular Selectors ───────────────────────────────────────── */
export const selectInput = (s: RootState) => s.chat.input;
export const selectSubmittingChatDisable = (s: RootState) => s.chat.submittingChatDisableInput;
export const selectClarificationMessage = (s: RootState) => s.chat.clarificationMessage;
export const selectAgentMessages = (s: RootState) => s.chat.agentMessages;

/* ── Memoized Derived Selectors ───────────────────────────────── */

/** Number of agent messages (avoids re-render on array identity change when count is same) */
export const selectAgentMessageCount = createSelector(
    selectAgentMessages,
    (messages) => messages.length,
);

/** Whether a clarification is currently pending */
export const selectHasPendingClarification = createSelector(
    selectClarificationMessage,
    (msg) => msg !== null,
);

export default chatSlice.reducer;
