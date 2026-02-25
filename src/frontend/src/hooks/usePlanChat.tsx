import { useCallback } from "react";
import {
    AgentMessageType,
} from "../models";
import { PlanDataService } from "../services/PlanDataService";
import { ShowToastFn } from "../components/toast/InlineToaster";
import { createAgentMessage } from "../utils";
import {
    useAppDispatch,
    useAppSelector,
    selectInput,
    selectSubmittingChatDisableInput,
    selectPlanData,
    selectClarificationMessage,
    selectPlanApprovalRequest,
    setInput,
    setSubmittingChatDisableInput,
    addAgentMessage,
    setShowProcessingPlanSpinner,
} from "../store";

/**
 * Return type for the usePlanChat hook
 */
export interface UsePlanChatReturn {
    /** Current chat input value */
    input: string;
    /** Setter for chat input (dispatch wrapper) */
    setInputValue: (value: string) => void;
    /** Whether chat input should be disabled */
    submittingChatDisableInput: boolean;
    /** Handle chat form submission */
    handleOnchatSubmit: (chatInput: string) => Promise<void>;
}

/**
 * Hook that encapsulates chat submission logic for the PlanPage.
 *
 * Reads planData, clarificationMessage, and planApprovalRequest from
 * Redux via granular selectors. Dispatches chat slice actions directly.
 *
 * @param showToast    - toast notification function
 * @param dismissToast - dismiss a specific toast
 * @param scrollToBottom - scroll chat container to bottom
 */
export function usePlanChat(
    showToast: ShowToastFn,
    dismissToast: (id: any) => void,
    scrollToBottom: () => void
): UsePlanChatReturn {
    const dispatch = useAppDispatch();
    const input = useAppSelector(selectInput);
    const submittingChatDisableInput = useAppSelector(selectSubmittingChatDisableInput);
    const planData = useAppSelector(selectPlanData);
    const clarificationMessage = useAppSelector(selectClarificationMessage);
    const planApprovalRequest = useAppSelector(selectPlanApprovalRequest);

    const setInputValue = useCallback(
        (value: string) => dispatch(setInput(value)),
        [dispatch]
    );

    const handleOnchatSubmit = useCallback(
        async (chatInput: string) => {
            if (!chatInput.trim()) {
                showToast("Please enter a clarification", "error");
                return;
            }
            dispatch(setInput(""));

            if (!planData?.plan) return;
            dispatch(setSubmittingChatDisableInput(true));
            const id = showToast("Submitting clarification", "progress");

            try {
                await PlanDataService.submitClarification({
                    request_id: clarificationMessage?.request_id || "",
                    answer: chatInput,
                    plan_id: planData?.plan.id,
                    m_plan_id: planApprovalRequest?.id || "",
                });

                dispatch(setInput(""));
                dismissToast(id);
                showToast("Clarification submitted successfully", "success");

                const agentMessageData = createAgentMessage(
                    "human",
                    AgentMessageType.HUMAN_AGENT,
                    chatInput || "",
                    chatInput || ""
                );

                dispatch(addAgentMessage(agentMessageData));
                dispatch(setSubmittingChatDisableInput(true));
                dispatch(setShowProcessingPlanSpinner(true));
                scrollToBottom();
            } catch (error: any) {
                dispatch(setShowProcessingPlanSpinner(false));
                dismissToast(id);
                dispatch(setSubmittingChatDisableInput(false));
                showToast("Failed to submit clarification", "error");
            }
        },
        [
            planData?.plan,
            clarificationMessage,
            planApprovalRequest,
            showToast,
            dismissToast,
            scrollToBottom,
            dispatch,
        ]
    );

    return {
        input,
        setInputValue,
        submittingChatDisableInput,
        handleOnchatSubmit,
    };
}
