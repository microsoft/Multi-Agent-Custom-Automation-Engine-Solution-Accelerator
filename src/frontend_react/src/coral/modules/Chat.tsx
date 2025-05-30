// 🪸 Chat — Stream-enabled Frontend Chat UI
// This component is split into two clearly defined roles:
//
// ─────────────────────────────────────────────────────────────
// 💄 FRONTEND (owned by: designer/dev)
// - UI layout and rendering
// - Input control and scroll behavior
// - Markdown rendering
// - Streaming UI update on assistant response
//
// 🔗 BACKEND (owned by: backend dev)
// - Message submission (`onSendMessage`) — must yield string chunks
// - History persistence (`onSaveMessage`, `onLoadHistory`, `onClearHistory`) — optional
// ─────────────────────────────────────────────────────────────

import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypePrism from "rehype-prism";
import {
  Body1,
  Button,
  Tag,
  Tooltip as FluentTooltip,
  ToolbarDivider,
} from "@fluentui/react-components";
import { Copy, Send } from "../imports/bundleicons";
import { HeartRegular } from "@fluentui/react-icons";
import "./Chat.css";
import "./prism-material-oceanic.css";

// 🔌 PROPS CONTRACT (Frontend-Backend Integration)
interface ChatProps {
  userId: string;

  // 🔗 BACKEND DEV: Required if streaming enabled
  // Sends user input and chat history to backend and yields assistant response chunks
  onSendMessage?: (
    input: string,
    history: { role: string; content: string }[]
  ) => AsyncIterable<string>;

  // 🔗 BACKEND DEV: Optional
  // Used for chat history persistence (localStorage, DB, etc.)
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
  // 🧠 STATE — Frontend-owned
  const [messages, setMessages] = useState<{ role: string; content: string }[]>(
    []
  );
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [inputHeight, setInputHeight] = useState(0);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputContainerRef = useRef<HTMLDivElement>(null);

  // 🔄 LIFECYCLE: Load chat history — Backend owned
  useEffect(() => {
    if (onLoadHistory) {
      onLoadHistory(userId)
        .then((history) => {
          if (history) setMessages(history);
        })
        .catch(() => {
          console.error("Failed to load chat history.");
        });
    }
  }, [onLoadHistory, userId]);

  // 🌀 UI: Auto-scroll to bottom on new message
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop =
        messagesContainerRef.current.scrollHeight;
      setShowScrollButton(false);
    }
  }, [messages]);

  // 🧭 UI: Show scroll button if user is far from bottom
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

  // 📏 UI: Track input container height to offset scroll button
  useEffect(() => {
    if (inputContainerRef.current) {
      setInputHeight(inputContainerRef.current.offsetHeight);
    }
  }, [input, isFocused]);

  // 🎯 UI: Scroll to bottom programmatically
  const scrollToBottom = () => {
    messagesContainerRef.current?.scrollTo({
      top: messagesContainerRef.current.scrollHeight,
      behavior: "smooth",
    });
    setShowScrollButton(false);
  };

  // 📋 COPY FUNCTION — Frontend owned
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text).catch((err) => {
      console.error("Failed to copy text:", err);
    });
  };

  // 📩 SEND MESSAGE — Backend required if streaming is enabled
  const sendMessage = async () => {
    if (!input.trim()) return;

    const updatedMessages = [...messages, { role: "user", content: input }];
    setMessages(updatedMessages);
    setInput("");
    setIsTyping(true);
    textareaRef.current && (textareaRef.current.style.height = "auto");

    try {
      if (onSendMessage) {
        // Streamed response handling
        let assistantContent = "";
        setMessages([...updatedMessages, { role: "assistant", content: "" }]);

        for await (const chunk of onSendMessage(input, updatedMessages)) {
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

        // 🔗 Optional backend hook
        onSaveMessage?.(userId, [
          ...updatedMessages,
          { role: "assistant", content: assistantContent },
        ]);
      } else {
        // Fallback message if no backend wired up
        setMessages([
          ...updatedMessages,
          { role: "assistant", content: "🤖 No backend connected yet." },
        ]);
      }
    } catch (err) {
      console.error("Send Message Error:", err);
      setMessages([
        ...updatedMessages,
        {
          role: "assistant",
          content: "Oops! Something went wrong sending your message.",
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  // 🧽 CLEAR CHAT — Optional backend hook
  const clearChat = () => {
    setMessages([]);
    onClearHistory?.(userId);
  };

  return (
    <div className="chat-container">
      {/* 💬 MESSAGES DISPLAY — Frontend owned */}
      <div
        className="messages"
        ref={messagesContainerRef}
        style={{ flex: 1, overflowY: "auto", minHeight: 0 }}
      >
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <Body1>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  whiteSpace: "pre-wrap",
                  width: "100%",
                }}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypePrism]}
                >
                  {msg.content}
                </ReactMarkdown>

                {/* ❤️ COPY + LIKE for assistant messages */}
                {/* ONLY COPY BUTTON IS FUNCTIONAL FOR NOW */}
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
                        onClick={() =>
                          console.log("Heart clicked for response:", msg.content)
                        }
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
        ))}
      </div>

      {/* 🔽 SCROLL TO BOTTOM — if user scrolls up */}
      {showScrollButton && (
        <Tag
          onClick={scrollToBottom}
          className="scroll-to-bottom"
          shape="circular"
          style={{
            bottom: inputHeight,
            backgroundColor: "var(--colorNeutralBackgroundAlpha2)",
            backdropFilter: "saturate(180%) blur(16px)",
          }}
        >
          Back to bottom
        </Tag>
      )}

      {/* 🖊 INPUT + ACTIONS — Frontend owned */}
      <div
        className={`input-wrapper ${isFocused ? "focused" : ""}`}
        ref={inputContainerRef}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            if (textareaRef.current) {
              textareaRef.current.style.height = "auto";
              textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
            }
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Type a message..."
          rows={1}
          className="input-field"
        />

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <FluentTooltip content="AI-generated content may be incorrect." relationship="label">
            <Tag appearance="filled" size="small">AI Generated</Tag>
          </FluentTooltip>

          <div style={{ display: "flex" }}>
            <Button appearance="transparent" onClick={sendMessage} icon={<Send />} />
            <ToolbarDivider />
            <Button appearance="transparent" onClick={sendMessage} icon={<Send />} />
          </div>
        </div>

        <span className="focus-indicator" />
      </div>

      {/* 🧼 CLEAR BUTTON — Backend optional */}
      {onClearHistory && (
        <button onClick={clearChat}>Clear Chat</button>
      )}
    </div>
  );
};

export default Chat;
