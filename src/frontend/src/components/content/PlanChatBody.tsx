import ChatInput from "@/coral/modules/ChatInput";
import { PlanChatProps } from "@/models";
import { Button, Caption1 } from "@fluentui/react-components";
import { Send } from "@/coral/imports/bundleicons";
import { Attach20Regular } from "@fluentui/react-icons";
import { useRef } from "react";

interface SimplifiedPlanChatProps extends PlanChatProps {
    planData: any;
    input: string;
    setInput: (input: string) => void;
    submittingChatDisableInput: boolean;
    OnChatSubmit: (input: string) => void;
    waitingForPlan: boolean;
    onDatasetUpload?: (file: File) => void;
}

const PlanChatBody: React.FC<SimplifiedPlanChatProps> = ({
    planData,
    input,
    setInput,
    submittingChatDisableInput,
    OnChatSubmit,
    waitingForPlan,
    onDatasetUpload
}) => {
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file && onDatasetUpload) {
            onDatasetUpload(file);
            // Reset input so same file can be uploaded again
            event.target.value = '';
        }
    };

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
            <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.json"
                style={{ display: 'none' }}
                onChange={handleFileUpload}
            />
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
                    icon={<Attach20Regular />}
                    onClick={() => fileInputRef.current?.click()}
                    disabled={submittingChatDisableInput}
                    title="Upload dataset"
                    style={{
                        height: '32px',
                        width: '32px',
                        borderRadius: '4px',
                        backgroundColor: 'transparent',
                        border: 'none',
                        color: submittingChatDisableInput
                            ? 'var(--colorNeutralForegroundDisabled)'
                            : 'var(--colorBrandForeground1)',
                        marginRight: '8px',
                        flexShrink: 0,
                    }}
                />
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