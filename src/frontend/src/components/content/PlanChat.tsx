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
  ToolbarDivider,
} from "@fluentui/react-components";
import { DiamondRegular, HeartRegular } from "@fluentui/react-icons";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import "../../styles/PlanChat.css";
import "../../styles/Chat.css";
import "../../styles/prism-material-oceanic.css";
import { TaskService } from "@/services/TaskService";
import InlineToaster from "../toast/InlineToaster";
import ContentNotFound from "../NotFound/ContentNotFound";

const PlanChat: React.FC<PlanChatProps> = ({
  planData,
  input,
  loading,
  setInput,
  submittingChatDisableInput,
  OnChatSubmit,
}) => {
  const messages = planData?.messages || [];
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [inputHeight, setInputHeight] = useState(0);

  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputContainerRef = useRef<HTMLDivElement>(null);

  // Scroll to Bottom useEffect

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  //Scroll to Bottom Buttom

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      setShowScrollButton(scrollTop + clientHeight < scrollHeight - 100);
    };

    container.addEventListener("scroll", handleScroll);
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    if (inputContainerRef.current) {
      setInputHeight(inputContainerRef.current.offsetHeight);
    }
  }, [input]); // or [inputValue, submittingChatDisableInput]

  const scrollToBottom = () => {
    messagesContainerRef.current?.scrollTo({
      top: messagesContainerRef.current.scrollHeight,
      behavior: "smooth",
    });
    setShowScrollButton(false);
  };

  if (!planData) {
    // If no plan data, still show the chat input for user to provide clarifications
    return (
      <div className="chat-container">
        <div className="messages" ref={messagesContainerRef}>
          <div className="message-wrapper">
            <div className="message assistant">
              <div className="plan-chat-header">
                <div className="plan-chat-speaker">
                  <Body1 className="speaker-name">AI Assistant</Body1>
                  <Tag size="extra-small" shape="rounded" appearance="brand">
                    Ready
                  </Tag>
                </div>
              </div>
              <Body1>
                <div className="plan-chat-message-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypePrism]}>
                    Plan completed! Feel free to ask questions or provide additional clarifications.
                  </ReactMarkdown>
                </div>
              </Body1>
            </div>
          </div>
        </div>

        <div className="plan-chat-input-container" ref={inputContainerRef}>
          <div className="plan-chat-input-wrapper">
            <ChatInput
              value={input}
              placeholder="Ask questions or provide clarifications about your plan..."
              onChange={setInput}
              onEnter={() => OnChatSubmit(input)}
              disabledChat={submittingChatDisableInput}
            >
              <Button
                appearance="subtle"
                onClick={() => OnChatSubmit(input)}
                disabled={submittingChatDisableInput}
                icon={<Send />}
              />
            </ChatInput>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="chat-container">
      <div className="messages" ref={messagesContainerRef}>
        <div className="message-wrapper">
          {messages.map((msg, index) => {
            const isHuman = msg.source === AgentType.HUMAN;

            return (
              <div
                key={index}
                className={`message ${isHuman ? role.user : role.assistant}`}
              >
                {!isHuman && (
                  <div className="plan-chat-header">
                    <div className="plan-chat-speaker">
                      <Body1 className="speaker-name">
                        {TaskService.cleanTextToSpaces(msg.source)}
                      </Body1>
                      <Tag
                        size="extra-small"
                        shape="rounded"
                        appearance="brand"
                        className="bot-tag"
                      >
                        BOT
                      </Tag>
                    </div>
                  </div>
                )}

                <Body1>
                  <div className="plan-chat-message-content">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypePrism]}
                    >
                      {TaskService.cleanHRAgent(msg.content) || ""}
                    </ReactMarkdown>

                    {!isHuman && (
                      <div className="assistant-footer">
                        <div className="assistant-actions">
                          <div>
                            <Button
                              onClick={() =>
                                msg.content &&
                                navigator.clipboard.writeText(msg.content)
                              }
                              title="Copy Response"
                              appearance="subtle"
                              style={{ height: 28, width: 28 }}
                              icon={<Copy />}
                            />
                          </div>

                          <Tag
                            icon={<DiamondRegular />}
                            appearance="filled"
                            size="extra-small"
                          >
                            Sample data for demonstration purposes only.
                          </Tag>
                        </div>
                      </div>
                    )}
                  </div>
                </Body1>
              </div>
            );
          })}
        </div>
      </div>

      {showScrollButton && (
        <Tag
          onClick={scrollToBottom}
          className="scroll-to-bottom plan-chat-scroll-button"
          shape="circular"
          style={{
            bottom: inputHeight,
            position: "absolute", // ensure this or your class handles it
            right: 16, // optional, for right alignment
            zIndex: 5,
          }}
        >
          Back to bottom
        </Tag>
      )}
      <InlineToaster />
      <div ref={inputContainerRef} className="plan-chat-input-container">
        <div className="plan-chat-input-wrapper">
          <ChatInput
            value={input}
            onChange={setInput}
            onEnter={() => OnChatSubmit(input)}
            disabledChat={
              planData?.enableChat ? submittingChatDisableInput : true
            }
            placeholder="Add more info to this task..."
          >
            <Button
              appearance="transparent"
              onClick={() => OnChatSubmit(input)}
              icon={<Send />}
              disabled={
                planData?.enableChat ? submittingChatDisableInput : true
              }
            />
          </ChatInput>
        </div>
      </div>
    </div>
  );
};

export default PlanChat;
