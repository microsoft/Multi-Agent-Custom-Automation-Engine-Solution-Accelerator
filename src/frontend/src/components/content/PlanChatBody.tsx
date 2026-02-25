import ChatInput from "@/coral/modules/ChatInput";
import { PlanChatProps } from "@/models";
import { Button } from "@fluentui/react-components";
import { Send } from "@/coral/imports/bundleicons";
import React, { useCallback, useMemo } from "react";

interface SimplifiedPlanChatProps extends PlanChatProps {
    planData: any;
    input: string;
    setInput: (input: string) => void;
    submittingChatDisableInput: boolean;
    OnChatSubmit: (input: string) => void;
    waitingForPlan: boolean;
}

const PlanChatBody: React.FC<SimplifiedPlanChatProps> = React.memo(({
    input,
    setInput,
    submittingChatDisableInput,
    OnChatSubmit,
}) => {
    const handleEnter = useCallback(() => OnChatSubmit(input), [OnChatSubmit, input]);
    const handleSendClick = useCallback(() => OnChatSubmit(input), [OnChatSubmit, input]);
    const isDisabled = useMemo(
        () => submittingChatDisableInput || !input.trim(),
        [submittingChatDisableInput, input]
    );
    return (
        <div
            style={{
                bottom: 0,
                padding: '16px 24px',
                maxWidth: '800px',
                margin: '0 auto',
                marginBottom: '40px',
                width: '100%',
                boxSizing: 'border-box',
                zIndex: 10
            }}
        >
            <ChatInput
                value={input}
                onChange={setInput}
                onEnter={handleEnter}
                disabledChat={submittingChatDisableInput}
                placeholder="Type your message here..."
                style={{
                    fontSize: '16px',
                    borderRadius: '8px',
                    width: '100%',
                    boxSizing: 'border-box',
                }}
            >
                <Button
                    appearance="subtle"
                    className="home-input-send-button"
                    onClick={handleSendClick}
                    disabled={isDisabled}
                    icon={<Send />}
                    style={{
                        height: '32px',
                        width: '32px',
                        borderRadius: '4px',
                        backgroundColor: 'transparent',
                        border: 'none',
                        color: isDisabled
                            ? 'var(--colorNeutralForegroundDisabled)'
                            : 'var(--colorBrandForeground1)',
                        flexShrink: 0,
                    }}
                />
            </ChatInput>
        </div>
    );
});
PlanChatBody.displayName = 'PlanChatBody';

export default PlanChatBody;