/**
 * This file contains examples of how to use the API services.
 * These examples are not meant to be executed directly but
 * serve as documentation for developers.
 */

import {
    agentMessageService,
    feedbackService,
    planService,
    taskService
} from '../api';
import { useApi } from '../hooks';

/**
 * Example component for submitting a task
 */
const TaskSubmissionExample = () => {
    // Hook for submitting a task
    const {
        data: taskResponse,
        loading: isSubmitting,
        error: submissionError,
        execute: submitTask
    } = useApi(taskService.submitInputTask);

    // Function to handle task submission
    const handleSubmit = async (description: string) => {
        await submitTask({ description });
        // If successful, taskResponse will contain session_id and plan_id
    };

    return (
        <div>
            {isSubmitting && <p>Submitting task...</p>}
            {submissionError && <p>Error: {submissionError.message}</p>}
            {taskResponse && (
                <p>
                    Task submitted successfully! Plan ID: {taskResponse.plan_id},
                    Session ID: {taskResponse.session_id}
                </p>
            )}
        </div>
    );
};

/**
 * Example component for loading plans
 */
const PlansExample = () => {
    // Hook for fetching plans
    const {
        data: plans,
        loading: loadingPlans,
        error: plansError,
        execute: loadPlans
    } = useApi(planService.getPlans);

    // Function to handle loading plans
    const handleLoadPlans = async (sessionId?: string) => {
        await loadPlans(sessionId);
    };

    // Function to approve a step
    const handleApproveStep = async (
        planId: string,
        sessionId: string,
        stepId: string
    ) => {
        try {
            await planService.approveSteps(planId, sessionId, true, stepId);
            // Reload plans after approval
            await loadPlans();
        } catch (error) {
            console.error('Error approving step:', error);
        }
    };

    return (
        <div>
            {loadingPlans && <p>Loading plans...</p>}
            {plansError && <p>Error: {plansError.message}</p>}
            {plans && (
                <div>
                    <h2>Plans ({plans.length})</h2>
                    {plans.map(plan => (
                        <div key={plan.id}>
                            <h3>{plan.initial_goal}</h3>
                            <p>Status: {plan.overall_status}</p>
                            <p>Steps: {plan.total_steps}</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

/**
 * Example component for submitting clarification
 */
const ClarificationExample = () => {
    // Hook for submitting clarification
    const {
        data: clarificationResponse,
        loading: isSubmitting,
        error: submissionError,
        execute: submitClarification
    } = useApi(
        (planId: string, sessionId: string, clarification: string) =>
            feedbackService.submitClarification(planId, sessionId, clarification)
    );

    // Function to handle clarification submission
    const handleSubmit = async (
        planId: string,
        sessionId: string,
        clarification: string
    ) => {
        await submitClarification(planId, sessionId, clarification);
    };

    return (
        <div>
            {isSubmitting && <p>Submitting clarification...</p>}
            {submissionError && <p>Error: {submissionError.message}</p>}
            {clarificationResponse && (
                <p>Clarification submitted successfully!</p>
            )}
        </div>
    );
};

/**
 * Example component for loading agent messages
 */
const AgentMessagesExample = () => {
    // Hook for fetching agent messages
    const {
        data: messages,
        loading: loadingMessages,
        error: messagesError,
        execute: loadMessages
    } = useApi(agentMessageService.getAgentMessages);

    // Function to handle loading messages
    const handleLoadMessages = async (sessionId: string) => {
        await loadMessages(sessionId);
    };

    return (
        <div>
            {loadingMessages && <p>Loading messages...</p>}
            {messagesError && <p>Error: {messagesError.message}</p>}
            {messages && (
                <div>
                    <h2>Messages ({messages.length})</h2>
                    {messages.map(message => (
                        <div key={message.id}>
                            <p>
                                <strong>{message.source}:</strong> {message.content}
                            </p>
                            <small>{new Date(message.timestamp).toLocaleString()}</small>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

// Export examples
export {
    TaskSubmissionExample,
    PlansExample,
    ClarificationExample,
    AgentMessagesExample
};
