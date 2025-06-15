import HeaderTools from "@/coral/components/Header/HeaderTools";
import { Copy, Send } from "@/coral/imports/bundleicons";
import ChatInput from "@/coral/modules/ChatInput";
import remarkGfm from "remark-gfm";
import rehypePrism from "rehype-prism";
import { AgentType, PlanChatProps, role } from "@/models";
import {
    Body1,
    Button,
    Spinner,
    Tag,
    ToolbarDivider
} from "@fluentui/react-components";
import {
    HeartRegular,
} from "@fluentui/react-icons";
import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import "../../styles/PlanChat.css";
import "../../styles/Chat.css";
import "../../styles/prism-material-oceanic.css";
import { TaskService } from "@/services/TaskService";
import InlineToaster from "../toast/InlineToaster";

const PlanChat: React.FC<PlanChatProps> = ({
    planData,
    input,
    loading,
    OnChatSubmit

}) => {
    const messages = planData?.messages || [];
    const [inputValue, setInput] = useState(input);
    const [isTyping, setIsTyping] = useState(false);
    const [showScrollButton, setShowScrollButton] = useState(false);
    const [inputHeight, setInputHeight] = useState(0);
    const [currentConversationId, setCurrentConversationId] = useState<string | undefined>(undefined);

    const messagesContainerRef = useRef<HTMLDivElement>(null);
    const inputContainerRef = useRef<HTMLDivElement>(null);

    const sendMessage = async () => { };

    const scrollToBottom = () => { };
    if (!planData) return <Spinner size="large" />;
    return (
        <div className="chat-container">
            <div className="messages" ref={messagesContainerRef}>
                <div className="message-wrapper">
                    {messages.map((msg, index) => {
                        const isHuman = msg.source === AgentType.HUMAN;

                        return (
                            <div key={index} className={`message ${isHuman ? role.user : role.assistant}`}>
                                {!isHuman && (
                                    <div className="plan-chat-header">
                                        <div className="plan-chat-speaker">
                                            <span className="speaker-name">{TaskService.cleanTextToSpaces(msg.source)}</span>
                                            <Tag size="extra-small" shape="rounded" appearance="filled" className="bot-tag">BOT</Tag>
                                        </div>
                                    </div>
                                )}

                                <Body1>
                                    <div className="plan-chat-message-content">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypePrism]}>
                                            {msg.content || ""}
                                        </ReactMarkdown>

                                        {!isHuman && (
                                            <div className="assistant-footer">
                                                <div className="assistant-actions">
                                                    <Button
                                                        onClick={() => msg.content && navigator.clipboard.writeText(msg.content)}
                                                        title="Copy Response"
                                                        appearance="subtle"
                                                        style={{ height: 28, width: 28 }}
                                                        icon={<Copy />}
                                                    />
                                                    <Tag size="extra-small">Sample data for demonstration purposes only.</Tag>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </Body1>
                            </div>
                        );
                    })}
                </div>

                {isTyping && (
                    <div className="typing-indicator">
                        <span>Thinking...</span>
                    </div>
                )}
            </div>

            {showScrollButton && (
                <Tag
                    onClick={scrollToBottom}
                    className="scroll-to-bottom plan-chat-scroll-button"
                    shape="circular"
                    style={{ bottom: inputHeight }}
                >
                    Back to bottom
                </Tag>
            )}
            <InlineToaster />
            <div ref={inputContainerRef} className="plan-chat-input-container">
                <div className="plan-chat-input-wrapper">
                    <ChatInput
                        value={inputValue}
                        onChange={setInput}
                        onEnter={() => OnChatSubmit(inputValue)}
                        disabledChat={!planData.enableChat}
                        placeholder="Add more info to this task..."
                    >
                        <Button
                            appearance="transparent"
                            onClick={() => OnChatSubmit(inputValue)}
                            icon={<Send />}
                            disabled={!planData?.enableChat && !inputValue.trim()}
                        />
                    </ChatInput>
                </div>
            </div>
        </div>

    );
};

export default PlanChat;
