import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypePrism from "rehype-prism";
import {
  Body1,
  Button,
  Tag,
  ToolbarDivider,
} from "@fluentui/react-components";
import { Copy, Send } from "../imports/bundleicons";
import { ChatDismiss20Regular, HeartRegular } from "@fluentui/react-icons";
import ChatInput from "./ChatInput";
import "./Chat.css";
import "./prism-material-oceanic.css";
import HeaderTools from "../components/Header/HeaderTools";

interface ChatProps {
  userId: string;
  children?: React.ReactNode;
  onSendMessage?: (
    input: string,
    history: { role: string; content: string }[]
  ) => AsyncIterable<string> | Promise<string>;
  onSaveMessage?: (
    userId: string,
    messages: { role: string; content: string }[]
  ) => void;
  onLoadHistory?: (
    userId: string
  ) => Promise<{ role: string; content: string }[]>;
  onClearHistory?: (userId: string) => void;
}

const Chat: React.FC<ChatProps> = ({
  userId,
  onSendMessage,
  onSaveMessage,
  onLoadHistory,
  onClearHistory,
}) => {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [inputHeight, setInputHeight] = useState(0);

  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        if (onLoadHistory) {
          const historyMessages = await onLoadHistory(userId);
          if (historyMessages && historyMessages.length > 0) {
            setMessages(historyMessages);
            return;
          }
        }
      } catch (err) {
        console.log("Failed to load chat history.", err);
      }
    };
    loadHistory();
  }, [onLoadHistory, userId]);

  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
      setShowScrollButton(false);
    }
  }, [messages]);

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
  }, [input]);

  const scrollToBottom = () => {
    messagesContainerRef.current?.scrollTo({
      top: messagesContainerRef.current.scrollHeight,
      behavior: "smooth",
    });
    setShowScrollButton(false);
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text).catch((err) => {
      console.log("Failed to copy text:", err);
    });
  };

  const isAsyncIterable = (value: any): value is AsyncIterable<any> => {
    return value !== null && typeof value === 'object' && Symbol.asyncIterator in value;
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const updatedMessages = [...messages, { role: "user", content: input }];
    setMessages(updatedMessages);
    setInput("");
    setIsTyping(true);

    try {
      if (onSendMessage) {
        setMessages([...updatedMessages, { role: "assistant", content: "" }]);
        const response = onSendMessage(input, updatedMessages);

        if (isAsyncIterable(response)) {
          let assistantContent = "";
          for await (const chunk of response) {
            assistantContent += chunk;
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                role: "assistant",
                content: assistantContent,
              };
              return updated;
            });
          }
          onSaveMessage?.(userId, [...updatedMessages, { role: "assistant", content: assistantContent }]);
        } else {
          const assistantResponse = await response;
          const newHistory = [...updatedMessages, { role: "assistant", content: assistantResponse }];
          setMessages(newHistory);
          onSaveMessage?.(userId, newHistory);
        }
      }
    } catch (err) {
      console.log("Send Message Error:", err);
      setMessages([
        ...updatedMessages,
        { role: "assistant", content: "Oops! Something went wrong sending your message." },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const clearChat = async () => {
    try {
      if (onClearHistory) {
        onClearHistory(userId);
      }
      setMessages([]);
    } catch (err) {
      console.log("Failed to clear chat history:", err);
    }
  };

  return (
    <div className="chat-container">
      <div className="messages" ref={messagesContainerRef}>
        <div className="message-wrapper">        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <Body1>
              <div style={{ display: "flex", flexDirection: "column", whiteSpace: "pre-wrap", width: "100%" }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypePrism]}>
                  {msg.content}
                </ReactMarkdown>
                {msg.role === "assistant" && (
                  <div className="assistant-footer">
                    <div className="assistant-actions">
                      <Button
                        onClick={() => handleCopy(msg.content)}
                        title="Copy Response"
                        appearance="subtle"
                        style={{ height: 28, width: 28 }}
                        icon={<Copy />}
                      />
                      <Button
                        onClick={() => {}}
                        title="Like"
                        appearance="subtle"
                        style={{ height: 28, width: 28 }}
                        icon={<HeartRegular />}
                      />
                    </div>
                  </div>
                )}
              </div>
            </Body1>
          </div>
        ))}</div>


        {isTyping && (
          <div className="typing-indicator">
            <span>Thinking...</span>
          </div>
        )}
      </div>

      {showScrollButton && (
        <Tag
          onClick={scrollToBottom}
          className="scroll-to-bottom"
          shape="circular"
          style={{
            bottom: inputHeight,
            backgroundColor: "transparent",
            border: '1px solid var(--colorNeutralStroke3)',
            backdropFilter: "saturate(180%) blur(16px)",
          }}
        >
          Back to bottom
        </Tag>
      )}

      <div ref={inputContainerRef} style={{ display: 'flex', width: '100%', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', width: '100%', maxWidth: '768px', margin: '0px 16px' }}>
          <ChatInput
            value={input}
            onChange={setInput}
            onEnter={sendMessage}

          >
            <Button
              appearance="transparent"
              onClick={sendMessage}
              icon={<Send />}
              disabled={isTyping || !input.trim()}
            />

            {messages.length > 0 && (
              <HeaderTools>
                <ToolbarDivider />
                <Button

                  onClick={clearChat}
                  appearance="transparent"
                  icon={<ChatDismiss20Regular />}
                  disabled={isTyping || messages.length === 0} />

              </HeaderTools>

            )}

          </ChatInput>
        </div>

      </div>


    </div>
  );
};

export default Chat;
