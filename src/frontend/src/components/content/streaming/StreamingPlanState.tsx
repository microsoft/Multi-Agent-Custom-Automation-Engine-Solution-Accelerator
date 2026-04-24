import React, { useEffect, useRef, useState } from "react";
import { Spinner } from "@fluentui/react-components";

const formatElapsedTime = (totalSeconds: number): string => {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    if (minutes <= 0) {
        return `${seconds}sec`;
    }

    return `${minutes}min ${seconds}sec`;
};

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

// Self-contained component with elapsed timer and rotating stage messages
// Pattern adopted from content-generation-solution-accelerator
const PlanExecutionMessage: React.FC = () => {
    const [elapsed, setElapsed] = useState(0);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    useEffect(() => {
        intervalRef.current = setInterval(() => {
            setElapsed(prev => prev + 1);
        }, 1000);
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, []);

    // Rotate stage messages based on elapsed time
    let stageMessage: string;
    if (elapsed < 8) {
        stageMessage = 'Processing your plan and coordinating with AI agents...';
    } else if (elapsed < 20) {
        stageMessage = 'Assigning tasks to specialized agents...';
    } else if (elapsed < 35) {
        stageMessage = 'Agents are analyzing and researching...';
    } else if (elapsed < 50) {
        stageMessage = 'Compiling results from agents...';
    } else {
        stageMessage = 'Finalizing responses...';
    }

    const elapsedSuffix = elapsed > 0 ? ` (${formatElapsedTime(elapsed)})` : '';

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
                    {`${stageMessage}${elapsedSuffix}`}
                </span>
            </div>
        </div>
    );
};

export { PlanExecutionMessage, renderThinkingState };