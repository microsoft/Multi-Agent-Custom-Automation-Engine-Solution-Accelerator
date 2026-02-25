import { useCallback, useEffect } from "react";
import {
    WebsocketMessageType,
    MPlanData,
    AgentMessageData,
    AgentMessageType,
    AgentType,
    PlanStatus,
    ParsedUserClarification,
    StreamMessage,
} from "../models";
import { PlanDataService } from "../services/PlanDataService";
import webSocketService from "../services/WebSocketService";
import { ShowToastFn } from "../components/toast/InlineToaster";
import { createAgentMessage, extractNestedContent, formatErrorMessage } from "../utils";
import { useChatHistorySave } from "./useChatHistorySave";
import {
    useAppDispatch,
    useAppSelector,
    selectContinueWithWebsocketFlow,
    selectPlanData,
    selectStreamingMessageBuffer,
    setPlanApprovalRequest as setPlanApprovalRequestAction,
    setWaitingForPlan,
    setShowProcessingPlanSpinner,
    appendToStreamingMessageBuffer,
    setShowBufferingText,
    setClarificationMessage,
    addAgentMessage,
    setSubmittingChatDisableInput,
    addStreamingMessage,
    setWsConnected,
    setSelectedTeam,
    updatePlanStatus,
    handlePlanReceived,
    triggerReloadLeftList,
} from "../store";

/**
 * Minimal callback interface — only non-Redux concerns remain.
 */
export interface PlanWebSocketCallbacks {
    scrollToBottom: () => void;
    showToast: ShowToastFn;
}

/**
 * Hook that encapsulates all WebSocket event listeners for the PlanPage.
 *
 * Reads planData, continueWithWebsocketFlow, and streamingMessageBuffer
 * from Redux via granular selectors.  Dispatches slice actions directly
 * instead of receiving 15+ setter callbacks.
 *
 * Handles:
 * - PLAN_APPROVAL_REQUEST
 * - AGENT_MESSAGE_STREAMING
 * - USER_CLARIFICATION_REQUEST
 * - AGENT_TOOL_MESSAGE
 * - FINAL_RESULT_MESSAGE
 * - ERROR_MESSAGE
 * - AGENT_MESSAGE
 * - WebSocket connection lifecycle
 */
export function usePlanWebSocket(
    planId: string | undefined,
    callbacks: PlanWebSocketCallbacks
) {
    const dispatch = useAppDispatch();
    const continueWithWebsocketFlow = useAppSelector(selectContinueWithWebsocketFlow);
    const planData = useAppSelector(selectPlanData);
    const streamingMessageBuffer = useAppSelector(selectStreamingMessageBuffer);

    const { scrollToBottom, showToast } = callbacks;

    // Embed chat-history persistence so processAgentMessage is self-contained
    const { processAgentMessage } = useChatHistorySave(
        useCallback(() => dispatch(triggerReloadLeftList()), [dispatch])
    );

    // PLAN_APPROVAL_REQUEST handler
    useEffect(() => {
        const unsubscribe = webSocketService.on(
            WebsocketMessageType.PLAN_APPROVAL_REQUEST,
            (approvalRequest: any) => {
                let mPlanData: MPlanData | null = null;

                if (approvalRequest.parsedData) {
                    mPlanData = approvalRequest.parsedData;
                } else if (approvalRequest.data && typeof approvalRequest.data === "object") {
                    mPlanData = approvalRequest.data.parsedData ?? approvalRequest.data;
                } else if (approvalRequest.rawData) {
                    mPlanData = PlanDataService.parsePlanApprovalRequest(approvalRequest.rawData);
                } else {
                    mPlanData = PlanDataService.parsePlanApprovalRequest(approvalRequest);
                }

                if (mPlanData) {
                    dispatch(handlePlanReceived(mPlanData));
                    scrollToBottom();
                }
            }
        );
        return () => unsubscribe();
    }, [scrollToBottom, dispatch]);

    // AGENT_MESSAGE_STREAMING handler
    useEffect(() => {
        const unsubscribe = webSocketService.on(
            WebsocketMessageType.AGENT_MESSAGE_STREAMING,
            (streamingMessage: any) => {
                const line = PlanDataService.simplifyHumanClarification(streamingMessage.data.content);
                dispatch(setShowBufferingText(true));
                dispatch(appendToStreamingMessageBuffer(line));
            }
        );
        return () => unsubscribe();
    }, [dispatch]);

    // USER_CLARIFICATION_REQUEST handler
    useEffect(() => {
        const unsubscribe = webSocketService.on(
            WebsocketMessageType.USER_CLARIFICATION_REQUEST,
            (clarificationMessage: any) => {
                if (!clarificationMessage) {
                    return;
                }
                const agentMessageData = createAgentMessage(
                    AgentType.GROUP_CHAT_MANAGER,
                    AgentMessageType.AI_AGENT,
                    clarificationMessage.data.question || "",
                    clarificationMessage.data || "",
                    clarificationMessage.timestamp || Date.now()
                );
                dispatch(setClarificationMessage(clarificationMessage.data as ParsedUserClarification | null));
                dispatch(addAgentMessage(agentMessageData));
                dispatch(setShowBufferingText(false));
                dispatch(setShowProcessingPlanSpinner(false));
                dispatch(setSubmittingChatDisableInput(false));
                scrollToBottom();
                processAgentMessage(agentMessageData, planData);
            }
        );
        return () => unsubscribe();
    }, [
        scrollToBottom,
        planData,
        processAgentMessage,
        dispatch,
    ]);

    // AGENT_TOOL_MESSAGE handler
    useEffect(() => {
        const unsubscribe = webSocketService.on(
            WebsocketMessageType.AGENT_TOOL_MESSAGE,
            (_toolMessage: any) => {
            }
        );
        return () => unsubscribe();
    }, []);

    // FINAL_RESULT_MESSAGE handler
    useEffect(() => {
        const unsubscribe = webSocketService.on(
            WebsocketMessageType.FINAL_RESULT_MESSAGE,
            (finalMessage: any) => {
                if (!finalMessage) {
                    return;
                }
                const agentMessageData = createAgentMessage(
                    AgentType.GROUP_CHAT_MANAGER,
                    AgentMessageType.AI_AGENT,
                    "🎉🎉 " + (finalMessage.data?.content || ""),
                    finalMessage
                );

                if (finalMessage?.data?.status === PlanStatus.COMPLETED) {
                    dispatch(setShowBufferingText(true));
                    dispatch(setShowProcessingPlanSpinner(false));
                    dispatch(addAgentMessage(agentMessageData));
                    dispatch(setSelectedTeam(planData?.team || null));
                    scrollToBottom();

                    dispatch(updatePlanStatus(PlanStatus.COMPLETED));

                    webSocketService.disconnect();
                    processAgentMessage(agentMessageData, planData, true, streamingMessageBuffer);
                }
            }
        );
        return () => unsubscribe();
    }, [
        scrollToBottom,
        planData,
        processAgentMessage,
        streamingMessageBuffer,
        dispatch,
    ]);

    // ERROR_MESSAGE handler
    useEffect(() => {
        const unsubscribe = webSocketService.on(
            WebsocketMessageType.ERROR_MESSAGE,
            (errorMessage: any) => {
                const errorContent = extractNestedContent(errorMessage);

                const errorAgentMessage = createAgentMessage(
                    "system",
                    AgentMessageType.SYSTEM_AGENT,
                    formatErrorMessage(errorContent),
                    errorMessage || ""
                );

                dispatch(addAgentMessage(errorAgentMessage));
                dispatch(setShowProcessingPlanSpinner(false));
                dispatch(setShowBufferingText(false));
                dispatch(setSubmittingChatDisableInput(false));
                scrollToBottom();
                showToast(errorContent, "error");
            }
        );
        return () => unsubscribe();
    }, [
        scrollToBottom,
        showToast,
        dispatch,
    ]);

    // AGENT_MESSAGE handler
    useEffect(() => {
        const unsubscribe = webSocketService.on(
            WebsocketMessageType.AGENT_MESSAGE,
            (agentMessage: any) => {
                const agentMessageData = agentMessage.data as AgentMessageData;
                if (agentMessageData) {
                    agentMessageData.content = PlanDataService.simplifyHumanClarification(
                        agentMessageData?.content
                    );
                    dispatch(addAgentMessage(agentMessageData));
                    dispatch(setShowProcessingPlanSpinner(true));
                    scrollToBottom();
                    processAgentMessage(agentMessageData, planData);
                }
            }
        );
        return () => unsubscribe();
    }, [scrollToBottom, planData, processAgentMessage, dispatch]);

    // WebSocket connection lifecycle
    useEffect(() => {
        if (planId && continueWithWebsocketFlow) {
            const connectWebSocket = async () => {
                try {
                    await webSocketService.connect(planId);
                } catch (error) {
                    console.error("WebSocket connection failed:", error);
                }
            };

            connectWebSocket();

            const handleConnectionChange = (connected: boolean) => {
                dispatch(setWsConnected(connected));
            };

            const handleStreamingMessage = (message: StreamMessage) => {
                if (message.data && message.data.plan_id) {
                    dispatch(addStreamingMessage(message.data));
                }
            };

            const handlePlanApprovalResponse = (_message: StreamMessage) => {
                // no-op: handled by PLAN_APPROVAL_REQUEST listener
            };

            const handlePlanApprovalRequest = (_message: StreamMessage) => {
                // no-op: handled by PLAN_APPROVAL_REQUEST listener above
            };

            const unsubscribeConnection = webSocketService.on("connection_status", (message) => {
                handleConnectionChange(message.data?.connected || false);
            });
            const unsubscribeStreaming = webSocketService.on(
                WebsocketMessageType.AGENT_MESSAGE,
                handleStreamingMessage
            );
            const unsubscribePlanApproval = webSocketService.on(
                WebsocketMessageType.PLAN_APPROVAL_RESPONSE,
                handlePlanApprovalResponse
            );
            const unsubscribePlanApprovalRequest = webSocketService.on(
                WebsocketMessageType.PLAN_APPROVAL_REQUEST,
                handlePlanApprovalRequest
            );
            const unsubscribeParsedPlanApprovalRequest = webSocketService.on(
                WebsocketMessageType.PLAN_APPROVAL_REQUEST,
                handlePlanApprovalRequest
            );

            return () => {
                unsubscribeConnection();
                unsubscribeStreaming();
                unsubscribePlanApproval();
                unsubscribePlanApprovalRequest();
                unsubscribeParsedPlanApprovalRequest();
                webSocketService.disconnect();
            };
        }
    }, [planId, continueWithWebsocketFlow, dispatch]);
}
