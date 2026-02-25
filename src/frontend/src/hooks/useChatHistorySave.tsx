import { useCallback } from "react";
import { AgentMessageData, ProcessedPlanData } from "../models";
import { PlanDataService } from "../services/PlanDataService";
import { apiService } from "../api/apiService";

export interface UseChatHistorySaveReturn {
    /**
     * Persist an agent message to the backend (fire-and-forget).
     *
     * @param agentMessageData  - the message to persist
     * @param planData          - current plan context
     * @param isFinal           - whether this is the final message in a conversation
     * @param streamingMessage  - the accumulated streaming buffer text
     * @returns a promise that resolves when persistence is done
     */
    processAgentMessage: (
        agentMessageData: AgentMessageData,
        planData: ProcessedPlanData | any,
        isFinal?: boolean,
        streamingMessage?: string
    ) => Promise<any>;
}

/**
 * Hook that encapsulates persisting agent messages to the backend.
 *
 * After a successful persist of a *final* message, it triggers a
 * delayed reload of the task list via the provided callback.
 *
 * @param onFinalMessagePersisted - callback invoked after a final message is saved
 */
export function useChatHistorySave(
    onFinalMessagePersisted?: () => void
): UseChatHistorySaveReturn {
    const processAgentMessage = useCallback(
        (
            agentMessageData: AgentMessageData,
            planData: ProcessedPlanData | any,
            isFinal = false,
            streamingMessage = ""
        ): Promise<any> => {
            const agentMessageResponse = PlanDataService.createAgentMessageResponse(
                agentMessageData,
                planData,
                isFinal,
                streamingMessage
            );
            return apiService
                .sendAgentMessage(agentMessageResponse)
                .then(() => {
                    if (isFinal && onFinalMessagePersisted) {
                        setTimeout(() => onFinalMessagePersisted(), 1000);
                    }
                })
                .catch((err) => {
                    console.warn("[agent_message][persist-failed]", err);
                    if (isFinal && onFinalMessagePersisted) {
                        setTimeout(() => onFinalMessagePersisted(), 1000);
                    }
                });
        },
        [onFinalMessagePersisted]
    );

    return { processAgentMessage };
}

export default useChatHistorySave;
