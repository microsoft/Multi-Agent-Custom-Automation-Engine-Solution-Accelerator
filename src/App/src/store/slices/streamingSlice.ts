/**
 * Streaming Slice — WebSocket streaming buffer and related flags.
 */
import { createSlice, createSelector, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../store';
import { StreamingPlanUpdate } from '@/models';

export interface StreamingState {
    /** Streaming plan updates from WebSocket */
    streamingMessages: StreamingPlanUpdate[];
    /** Buffered streaming text (accumulated agent output) */
    streamingMessageBuffer: string;
    /** Should the buffering text indicator be visible? */
    showBufferingText: boolean;
}

const initialState: StreamingState = {
    streamingMessages: [],
    streamingMessageBuffer: '',
    showBufferingText: false,
};

const streamingSlice = createSlice({
    name: 'streaming',
    initialState,
    reducers: {
        setStreamingMessages(state, action: PayloadAction<StreamingPlanUpdate[]>) {
            state.streamingMessages = action.payload as any;
        },
        addStreamingMessage(state, action: PayloadAction<StreamingPlanUpdate>) {
            state.streamingMessages.push(action.payload as any);
        },
        setStreamingMessageBuffer(state, action: PayloadAction<string>) {
            state.streamingMessageBuffer = action.payload;
        },
        appendToStreamingBuffer(state, action: PayloadAction<string>) {
            state.streamingMessageBuffer += action.payload;
        },
        setShowBufferingText(state, action: PayloadAction<boolean>) {
            state.showBufferingText = action.payload;
        },
        resetStreaming() {
            return { ...initialState };
        },
    },
});

export const {
    setStreamingMessages,
    addStreamingMessage,
    setStreamingMessageBuffer,
    appendToStreamingBuffer,
    setShowBufferingText,
    resetStreaming,
} = streamingSlice.actions;

/* ── Granular Selectors ───────────────────────────────────────── */
export const selectStreamingMessages = (s: RootState) => s.streaming.streamingMessages;
export const selectStreamingMessageBuffer = (s: RootState) => s.streaming.streamingMessageBuffer;
export const selectShowBufferingText = (s: RootState) => s.streaming.showBufferingText;

/* ── Memoized Derived Selectors ───────────────────────────────── */

/** Number of streaming messages (stable primitive — avoids child re-renders) */
export const selectStreamingMessageCount = createSelector(
    selectStreamingMessages,
    (messages) => messages.length,
);

/** Whether we have buffered content ready to display */
export const selectHasStreamingBuffer = createSelector(
    selectStreamingMessageBuffer,
    (buffer) => buffer.length > 0,
);

export default streamingSlice.reducer;
