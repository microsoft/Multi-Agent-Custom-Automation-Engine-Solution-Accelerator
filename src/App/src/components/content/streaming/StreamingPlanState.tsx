import { Spinner } from "@fluentui/react-components";
import ProcessingStatusIndicator from "../../common/ProcessingStatusIndicator.tsx";

// Simple thinking message to show while creating plan
const renderThinkingState = (waitingForPlan: boolean) => {
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
                {/* Bot Avatar */}
                {/* <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--colorNeutralBackground3)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                }}>
                    <div style={{
                        width: '16px',
                        height: '16px',
                        backgroundColor: 'var(--colorBrandBackground)',
                        borderRadius: '2px'
                    }} />
                </div> */}

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
};

// Simple message to show while executing the plan
const renderPlanExecutionMessage = (
    processingElapsedSeconds?: number,
    processingStatusMessage = 'Processing your plan and coordinating with AI agents...',
) => {
    return (
        <ProcessingStatusIndicator
            message={processingStatusMessage}
            elapsedSeconds={processingElapsedSeconds}
        />
    );
};

export { renderPlanExecutionMessage, renderThinkingState };