import React from "react";
import { Spinner } from "@fluentui/react-components";

// ─── ThinkingState ───────────────────────────────────────────────────────────

/** Props for the ThinkingState component */
export interface ThinkingStateProps {
    /** Whether we are still waiting for the plan to arrive */
    waitingForPlan: boolean;
}

/**
 * Displays a spinner + "Creating your plan..." while the plan is being generated.
 * Handles a single message type: thinking / loading state.
 */
const ThinkingState: React.FC<ThinkingStateProps> = React.memo(({ waitingForPlan }) => {
    if (!waitingForPlan) return null;

    return (
        <div style={{
            maxWidth: '800px',
            margin: '0 auto 32px auto',
            padding: '0 24px'
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '16px'
            }}>
                {/* Thinking Message */}
                <div style={{ flex: 1, maxWidth: 'calc(100% - 48px)' }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        padding: '16px 0',
                        color: 'var(--colorNeutralForeground2)',
                        fontSize: '14px'
                    }}>
                        <Spinner size="small" />
                        <span>Creating your plan...</span>
                    </div>
                </div>
            </div>
        </div>
    );
});
ThinkingState.displayName = 'ThinkingState';

// ─── PlanExecutionMessage ────────────────────────────────────────────────────

/**
 * Displays a banner while the plan is being executed by AI agents.
 * Handles a single message type: execution-in-progress state.
 */
const PlanExecutionMessage: React.FC = React.memo(() => {
    return (
        <div style={{
            maxWidth: '800px',
            margin: '0 auto 32px auto',
            padding: '0 24px'
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                backgroundColor: 'var(--colorNeutralBackground2)',
                borderRadius: '8px',
                border: '1px solid var(--colorNeutralStroke1)',
                padding: '16px'
            }}>
                <Spinner size="small" />
                <span style={{
                    fontSize: '14px',
                    color: 'var(--colorNeutralForeground1)',
                    fontWeight: '500'
                }}>
                    Processing your plan and coordinating with AI agents...
                </span>
            </div>
        </div>
    );
});
PlanExecutionMessage.displayName = 'PlanExecutionMessage';

// ─── Backward-compatible render functions (deprecated) ───────────────────────

/** @deprecated Use `<ThinkingState>` component instead */
const renderThinkingState = (waitingForPlan: boolean) => (
    <ThinkingState waitingForPlan={waitingForPlan} />
);

/** @deprecated Use `<PlanExecutionMessage>` component instead */
const renderPlanExecutionMessage = () => <PlanExecutionMessage />;

export { ThinkingState, PlanExecutionMessage, renderPlanExecutionMessage, renderThinkingState };