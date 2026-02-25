import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { AgentMessageData, ParsedUserClarification, StreamingPlanUpdate } from '../../models';

/**
 * Chat slice - handles chat/messaging state
 */
export interface ChatState {
    /** User input in chat box */
    input: string;
    /** Whether chat input is disabled while submitting */
    submittingChatDisableInput: boolean;
    /** Agent messages in the conversation */
    agentMessages: AgentMessageData[];
    /** Streaming messages updates */
    streamingMessages: StreamingPlanUpdate[];
    /** Buffer for streaming message content */
    streamingMessageBuffer: string;
    /** Whether to show buffering text indicator */
    showBufferingText: boolean;
    /** Current clarification message from system */
    clarificationMessage: ParsedUserClarification | null;
}

const initialState: ChatState = {
    input: '',
    submittingChatDisableInput: true,
    agentMessages: [],
    streamingMessages: [],
    streamingMessageBuffer: '',
    showBufferingText: false,
    clarificationMessage: null,
};

const chatSlice = createSlice({
    name: 'chat',
    initialState,
    reducers: {
        setInput: (state, action: PayloadAction<string>) => {
            state.input = action.payload;
        },
        setSubmittingChatDisableInput: (state, action: PayloadAction<boolean>) => {
            state.submittingChatDisableInput = action.payload;
        },
        setAgentMessages: (state, action: PayloadAction<AgentMessageData[]>) => {
            state.agentMessages = action.payload;
        },
        addAgentMessage: (state, action: PayloadAction<AgentMessageData>) => {
            state.agentMessages.push(action.payload);
        },
        setStreamingMessages: (state, action: PayloadAction<StreamingPlanUpdate[]>) => {
            state.streamingMessages = action.payload;
        },
        addStreamingMessage: (state, action: PayloadAction<StreamingPlanUpdate>) => {
            state.streamingMessages.push(action.payload);
        },
        setStreamingMessageBuffer: (state, action: PayloadAction<string>) => {
            state.streamingMessageBuffer = action.payload;
        },
        appendToStreamingMessageBuffer: (state, action: PayloadAction<string>) => {
            state.streamingMessageBuffer += action.payload;
        },
        setShowBufferingText: (state, action: PayloadAction<boolean>) => {
            state.showBufferingText = action.payload;
        },
        setClarificationMessage: (state, action: PayloadAction<ParsedUserClarification | null>) => {
            state.clarificationMessage = action.payload;
        },
        /**
         * Reset chat state to initial values
         */
        resetChatState: () => initialState,
        /**
         * Clear streaming buffer and hide buffering text
         */
        clearStreamingBuffer: (state) => {
            state.streamingMessageBuffer = '';
            state.showBufferingText = false;
        },
    },
});

export const {
    setInput,
    setSubmittingChatDisableInput,
    setAgentMessages,
    addAgentMessage,
    setStreamingMessages,
    addStreamingMessage,
    setStreamingMessageBuffer,
    appendToStreamingMessageBuffer,
    setShowBufferingText,
    setClarificationMessage,
    resetChatState,
    clearStreamingBuffer,
} = chatSlice.actions;

export default chatSlice.reducer;
