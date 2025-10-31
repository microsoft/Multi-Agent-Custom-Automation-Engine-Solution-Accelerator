import ChatInput from "@/coral/modules/ChatInput";
import { PlanChatProps } from "@/models";
import { Button, Caption1 } from "@fluentui/react-components";
import { Send } from "@/coral/imports/bundleicons";

interface SimplifiedPlanChatProps extends PlanChatProps {
    planData: any;
    input: string;
    setInput: (input: string) => void;
    submittingChatDisableInput: boolean;
    OnChatSubmit: (input: string) => void;
    waitingForPlan: boolean;
}

const PlanChatBody: React.FC<SimplifiedPlanChatProps> = ({
    planData,
    input,
    setInput,
    submittingChatDisableInput,
    OnChatSubmit,
    waitingForPlan
}) => {
    return (
        <div
            style={{
                // position: 'sticky',
                bottom: 0,
                // backgroundColor: 'var(--colorNeutralBackground1)',
                // borderTop: '1px solid var(--colorNeutralStroke2)',
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
                onEnter={() => OnChatSubmit(input)}
                disabledChat={submittingChatDisableInput}
                placeholder="Type your message here..."
                style={{
                    fontSize: '16px',
                    borderRadius: '8px',
                    // border: '1px solid var(--colorNeutralStroke1)',
                    // backgroundColor: 'var(--colorNeutralBackground1)',
                    width: '100%',
                    boxSizing: 'border-box',
                }}
            >
                <Button
                    appearance="subtle"
                    className="home-input-send-button"
                    onClick={() => OnChatSubmit(input)}
                    disabled={submittingChatDisableInput || !input.trim()}
                    icon={<Send />}
                    style={{
                        height: '32px',
                        width: '32px',
                        borderRadius: '4px',
                        backgroundColor: 'transparent',
                        border: 'none',
                        color: (submittingChatDisableInput || !input.trim())
                            ? 'var(--colorNeutralForegroundDisabled)'
                            : 'var(--colorBrandForeground1)',
                        flexShrink: 0,
                    }}
                />
            </ChatInput>
        </div>
    );
}

export default PlanChatBody;