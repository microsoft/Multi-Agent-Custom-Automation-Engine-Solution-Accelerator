/**
 * usePlanWebSocket — extracts all WebSocket event subscriptions
 * from PlanPage into one reusable hook.
 *
 * Dispatches Redux actions for each event type so PlanPage no longer
 * needs 7+ useEffect blocks for WebSocket handling.
 */
import React, { useEffect } from 'react';
import webSocketService from '@/services/WebSocketService';
import { PlanDataService } from '@/services/PlanDataService';
import { useAppDispatch, useAppSelector } from '@/state/hooks';
import {
    setShowProcessingPlanSpinner,
    setReloadLeftList,
    selectPlanData,
    selectContinueWithWebsocketFlow,
    selectPlanApproved,
    approvalRequestReceived,
    planCompletedFinal,
} from '@/state/slices/planSlice';
import {
    setSubmittingChatDisableInput,
    setClarificationMessage,
    addAgentMessage,
} from '@/state/slices/chatSlice';
import {
    appendToStreamingBuffer,
    setShowBufferingText,
    addStreamingMessage,
    selectStreamingMessageBuffer,
} from '@/state/slices/streamingSlice';
import { setWsConnected } from '@/state/slices/appSlice';
import { setSelectedTeam } from '@/state/slices/teamSlice';
import {
    WebsocketMessageType,
    MPlanData,
    AgentMessageData,
    AgentMessageType,
    AgentType,
    PlanStatus,
    ParsedUserClarification,
    StreamMessage,
    ProcessedPlanData,
} from '@/models';
import { APIService } from '@/api/apiService';

const apiService = new APIService();

import { ToastIntent } from '@/components/toast/InlineToaster';

interface UsePlanWebSocketProps {
    planId: string | undefined;
    scrollToBottom: () => void;
    formatErrorMessage: (content: string) => string;
    showToast: (content: React.ReactNode, intent?: ToastIntent, options?: { dismissible?: boolean; timeoutMs?: number | null }) => number;
}

/**
 * Creates an AgentMessageResponse and persists it, then optionally reloads the task list.
 */
function persistAgentMessage(
    agentMessageData: AgentMessageData,
    planData: ProcessedPlanData | null,
    dispatch: ReturnType<typeof useAppDispatch>,
    isFinal = false,
    streamingMessage = '',
) {
    if (!planData?.plan) return;

    const agentMessageResponse = PlanDataService.createAgentMessageResponse(
        agentMessageData,
        planData,
        isFinal,
        streamingMessage,
    );
    apiService
        .sendAgentMessage(agentMessageResponse)
        .then(() => {
            if (isFinal) {
                setTimeout(() => dispatch(setReloadLeftList(true)), 1000);
            }
        })
        .catch(() => {
            if (isFinal) {
                setTimeout(() => dispatch(setReloadLeftList(true)), 1000);
            }
        });
}

export function usePlanWebSocket({
    planId,
    scrollToBottom,
    formatErrorMessage,
    showToast,
}: UsePlanWebSocketProps) {
    const dispatch = useAppDispatch();
    const planData = useAppSelector(selectPlanData);
    const planApproved = useAppSelector(selectPlanApproved);
    const continueWithWebsocketFlow = useAppSelector(selectContinueWithWebsocketFlow);
    const streamingMessageBuffer = useAppSelector(selectStreamingMessageBuffer);

    // ── PLAN_APPROVAL_REQUEST ─────────────────────────────────────
    useEffect(() => {
        const unsub = webSocketService.on(
            WebsocketMessageType.PLAN_APPROVAL_REQUEST,
            (approvalRequest: any) => {
                let mPlanData: MPlanData | null = null;
                if (approvalRequest.parsedData) {
                    mPlanData = approvalRequest.parsedData;
                } else if (approvalRequest.data?.parsedData) {
                    mPlanData = approvalRequest.data.parsedData;
                } else if (approvalRequest.data && typeof approvalRequest.data === 'object') {
                    mPlanData = approvalRequest.data;
                } else if (approvalRequest.rawData) {
                    mPlanData = PlanDataService.parsePlanApprovalRequest(approvalRequest.rawData);
                } else {
                    mPlanData = PlanDataService.parsePlanApprovalRequest(approvalRequest);
                }
                if (mPlanData) {
                    /* P0: single compound action replaces 4 separate dispatches */
                    dispatch(approvalRequestReceived(mPlanData));
                    scrollToBottom();
                }
            },
        );
        return unsub;
    }, [dispatch, scrollToBottom]);

    // ── AGENT_MESSAGE_STREAMING ───────────────────────────────────
    useEffect(() => {
        const unsub = webSocketService.on(
            WebsocketMessageType.AGENT_MESSAGE_STREAMING,
            (msg: any) => {
                const line = PlanDataService.simplifyHumanClarification(msg.data.content);
                dispatch(setShowBufferingText(true));
                dispatch(appendToStreamingBuffer(line));
            },
        );
        return unsub;
    }, [dispatch]);

    // ── USER_CLARIFICATION_REQUEST ────────────────────────────────
    useEffect(() => {
        const unsub = webSocketService.on(
            WebsocketMessageType.USER_CLARIFICATION_REQUEST,
            (msg: any) => {
                if (!msg) return;
                const agentMessageData: AgentMessageData = {
                    agent: AgentType.GROUP_CHAT_MANAGER,
                    agent_type: AgentMessageType.AI_AGENT,
                    timestamp: msg.timestamp || Date.now(),
                    steps: [],
                    next_steps: [],
                    content: msg.data.question || '',
                    raw_data: msg.data || '',
                };
                dispatch(setClarificationMessage(msg.data as ParsedUserClarification));
                dispatch(addAgentMessage(agentMessageData));
                dispatch(setShowBufferingText(false));
                dispatch(setShowProcessingPlanSpinner(false));
                dispatch(setSubmittingChatDisableInput(false));
                scrollToBottom();
                persistAgentMessage(agentMessageData, planData, dispatch);
            },
        );
        return unsub;
    }, [dispatch, scrollToBottom, planData]);

    // ── AGENT_TOOL_MESSAGE (currently no-op, kept for future) ─────
    useEffect(() => {
        const unsub = webSocketService.on(WebsocketMessageType.AGENT_TOOL_MESSAGE, () => {});
        return unsub;
    }, []);

    // ── FINAL_RESULT_MESSAGE ──────────────────────────────────────
    useEffect(() => {
        const unsub = webSocketService.on(
            WebsocketMessageType.FINAL_RESULT_MESSAGE,
            (finalMessage: any) => {
                if (!finalMessage) return;
                const agentMessageData: AgentMessageData = {
                    agent: AgentType.GROUP_CHAT_MANAGER,
                    agent_type: AgentMessageType.AI_AGENT,
                    timestamp: Date.now(),
                    steps: [],
                    next_steps: [],
                    content: '\u{1F389}\u{1F389} ' + (finalMessage.data?.content || ''),
                    raw_data: finalMessage,
                };
                if (finalMessage?.data?.status === PlanStatus.COMPLETED) {
                    dispatch(setShowBufferingText(true));
                    dispatch(addAgentMessage(agentMessageData));
                    dispatch(setSelectedTeam(planData?.team || null));
                    /* P0: single compound action replaces setShowProcessingPlanSpinner(false) + markPlanCompleted() */
                    dispatch(planCompletedFinal());
                    scrollToBottom();
                    webSocketService.disconnect();
                    persistAgentMessage(agentMessageData, planData, dispatch, true, streamingMessageBuffer);
                }
            },
        );
        return unsub;
    }, [dispatch, scrollToBottom, planData, streamingMessageBuffer]);

    // ── ERROR_MESSAGE ─────────────────────────────────────────────
    useEffect(() => {
        const unsub = webSocketService.on(
            WebsocketMessageType.ERROR_MESSAGE,
            (errorMessage: any) => {
                let errorContent = 'An unexpected error occurred. Please try again later.';
                if (errorMessage?.data?.data?.content) {
                    const c = errorMessage.data.data.content.trim();
                    if (c.length > 0) errorContent = c;
                } else if (errorMessage?.data?.content) {
                    const c = errorMessage.data.content.trim();
                    if (c.length > 0) errorContent = c;
                } else if (errorMessage?.content) {
                    const c = errorMessage.content.trim();
                    if (c.length > 0) errorContent = c;
                } else if (typeof errorMessage === 'string') {
                    const c = errorMessage.trim();
                    if (c.length > 0) errorContent = c;
                }
                const errorAgent: AgentMessageData = {
                    agent: 'system',
                    agent_type: AgentMessageType.SYSTEM_AGENT,
                    timestamp: Date.now(),
                    steps: [],
                    next_steps: [],
                    content: formatErrorMessage(errorContent),
                    raw_data: errorMessage || '',
                };
                dispatch(addAgentMessage(errorAgent));
                dispatch(setShowProcessingPlanSpinner(false));
                dispatch(setShowBufferingText(false));
                dispatch(setSubmittingChatDisableInput(false));
                scrollToBottom();
                showToast(errorContent, 'error');
            },
        );
        return unsub;
    }, [dispatch, scrollToBottom, showToast, formatErrorMessage]);

    // ── AGENT_MESSAGE ─────────────────────────────────────────────
    useEffect(() => {
        const unsub = webSocketService.on(
            WebsocketMessageType.AGENT_MESSAGE,
            (agentMessage: any) => {
                // Only process agent messages after the user has approved the plan
                if (!planApproved) return;

                const agentMessageData = agentMessage.data as AgentMessageData;
                if (agentMessageData) {
                    agentMessageData.content = PlanDataService.simplifyHumanClarification(
                        agentMessageData?.content,
                    );
                    dispatch(addAgentMessage(agentMessageData));
                    dispatch(setShowProcessingPlanSpinner(true));
                    scrollToBottom();
                    persistAgentMessage(agentMessageData, planData, dispatch);
                }
            },
        );
        return unsub;
    }, [dispatch, scrollToBottom, planData, planApproved]);

    // ── WebSocket connect / disconnect lifecycle ──────────────────
    useEffect(() => {
        if (!planId || !continueWithWebsocketFlow) return;

        const connectWebSocket = async () => {
            try {
                await webSocketService.connect(planId);
            } catch (error) {
                console.log('WebSocket connection failed, continuing without real-time updates', error);
            }
        };
        connectWebSocket();

        const handleConnectionChange = (connected: boolean) => {
            dispatch(setWsConnected(connected));
        };

        const handleStreamingMessage = (message: StreamMessage) => {
            if (message.data?.plan_id) {
                dispatch(addStreamingMessage(message.data));
            }
        };

        const unsubConnection = webSocketService.on('connection_status', (msg) =>
            handleConnectionChange(msg.data?.connected || false),
        );
        const unsubStreaming = webSocketService.on(
            WebsocketMessageType.AGENT_MESSAGE,
            handleStreamingMessage,
        );
        const unsubApproval = webSocketService.on(WebsocketMessageType.PLAN_APPROVAL_RESPONSE, () => {});
        const unsubApprovalReq = webSocketService.on(WebsocketMessageType.PLAN_APPROVAL_REQUEST, () => {});

        return () => {
            unsubConnection();
            unsubStreaming();
            unsubApproval();
            unsubApprovalReq();
            webSocketService.disconnect();
        };
    }, [dispatch, planId, continueWithWebsocketFlow]);
}

export default usePlanWebSocket;
