/**
 * Cross-Slice Thunks
 *
 * Coordinated actions that dispatch to multiple slices in a single
 * logical operation.  These are regular thunk functions — RTK ships
 * with `redux-thunk` middleware by default, so `dispatch(fn)` works
 * out of the box.
 */
import type { AppDispatch } from './store';
import { resetPlanVariables } from './slices/planSlice';
import {
    setAgentMessages,
    setClarificationMessage,
    setStreamingMessages,
    clearStreamingBuffer,
} from './slices/chatSlice';
import { setWsConnected } from './slices/appSlice';
import { triggerReloadLeftList } from './slices/chatHistorySlice';

/**
 * Reset all plan-session-related state across plan, chat, app and
 * chatHistory slices.
 *
 * Called when:
 * - Loading a new plan (planId changes)
 * - Navigating away from the PlanPage
 */
export const resetPlanSession = () => (dispatch: AppDispatch) => {
    dispatch(resetPlanVariables());          // plan slice
    dispatch(setAgentMessages([]));           // chat slice
    dispatch(setClarificationMessage(null));  // chat slice
    dispatch(setStreamingMessages([]));       // chat slice
    dispatch(clearStreamingBuffer());         // chat slice (buffer + showBufferingText)
    dispatch(setWsConnected(false));          // app slice
    dispatch(triggerReloadLeftList());         // chatHistory slice
};
