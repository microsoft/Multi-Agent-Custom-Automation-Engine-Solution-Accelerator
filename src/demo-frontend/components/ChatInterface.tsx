'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Message structure for chat history
 */
export interface ChatMessage {
  /** Message role (user or assistant) */
  role: 'user' | 'assistant';
  /** Message content */
  content: string;
  /** Timestamp of the message */
  timestamp?: Date;
  /** Optional message ID */
  id?: string;
}

/**
 * Props for the ChatInterface component
 */
export interface ChatInterfaceProps {
  /** User identifier for session management */
  userId?: string;
  /** Callback to send a message and receive response */
  onSendMessage?: (
    input: string,
    history: ChatMessage[]
  ) => AsyncIterable<string> | Promise<string>;
  /** Callback to save message history */
  onSaveMessage?: (userId: string, messages: ChatMessage[]) => void;
  /** Callback to load message history */
  onLoadHistory?: (userId: string) => Promise<ChatMessage[]>;
  /** Callback to clear message history */
  onClearHistory?: (userId: string) => void;
  /** Placeholder text for input field */
  placeholder?: string;
  /** Welcome message shown when no messages */
  welcomeMessage?: string;
  /** Whether the component is in a loading state */
  loading?: boolean;
  /** Optional className for custom styling */
  className?: string;
  /** Maximum height of the chat container */
  maxHeight?: string;
}

/**
 * Send icon for message submit button
 */
const SendIcon = ({ className = 'h-5 w-5' }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <line x1="22" x2="11" y1="2" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);

/**
 * Copy icon for copying message content
 */
const CopyIcon = ({ className = 'h-4 w-4' }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
    <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
  </svg>
);

/**
 * Check icon for copy confirmation
 */
const CheckIcon = ({ className = 'h-4 w-4' }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

/**
 * Clear/trash icon for clearing chat
 */
const ClearIcon = ({ className = 'h-5 w-5' }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M3 6h18" />
    <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
    <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
  </svg>
);

/**
 * Arrow down icon for scroll to bottom
 */
const ArrowDownIcon = ({ className = 'h-4 w-4' }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <line x1="12" x2="12" y1="5" y2="19" />
    <polyline points="19 12 12 19 5 12" />
  </svg>
);

/**
 * Bot/AI icon for assistant messages
 */
const BotIcon = ({ className = 'h-6 w-6' }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect width="18" height="10" x="3" y="11" rx="2" />
    <circle cx="12" cy="5" r="2" />
    <path d="M12 7v4" />
    <line x1="8" x2="8" y1="16" y2="16" />
    <line x1="16" x2="16" y1="16" y2="16" />
  </svg>
);

/**
 * User icon for user messages
 */
const UserIcon = ({ className = 'h-6 w-6' }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

/**
 * Typing indicator dots animation
 */
const TypingIndicator: React.FC = () => (
  <div className="flex items-center gap-1.5 py-2 px-3">
    <span className="h-2 w-2 bg-brand rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
    <span className="h-2 w-2 bg-brand rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
    <span className="h-2 w-2 bg-brand rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
  </div>
);

/**
 * Skeleton component for loading state
 */
const ChatSkeleton: React.FC = () => (
  <div className="flex flex-col h-full animate-pulse">
    <div className="flex-1 p-4 space-y-4">
      <div className="flex items-start gap-3">
        <div className="h-8 w-8 bg-muted rounded-full" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-3/4 bg-muted rounded" />
          <div className="h-4 w-1/2 bg-muted rounded" />
        </div>
      </div>
      <div className="flex items-start gap-3 justify-end">
        <div className="flex-1 space-y-2">
          <div className="h-4 w-1/2 bg-muted rounded ml-auto" />
        </div>
        <div className="h-8 w-8 bg-muted rounded-full" />
      </div>
    </div>
    <div className="p-4 border-t border-border">
      <div className="h-12 bg-muted rounded-lg" />
    </div>
  </div>
);

/**
 * Welcome message component shown when chat is empty
 */
const WelcomeMessage: React.FC<{ message?: string }> = ({ message }) => (
  <div className="flex flex-col items-center justify-center h-full text-center p-8">
    <div className="p-4 bg-brand/10 rounded-full mb-4">
      <BotIcon className="h-10 w-10 text-brand" />
    </div>
    <h3 className="text-lg font-semibold text-foreground mb-2">
      AI Assistant
    </h3>
    <p className="text-muted-foreground max-w-sm">
      {message || "Hi there! I'm your AI assistant. How can I help you today?"}
    </p>
  </div>
);

/**
 * Check if a value is an async iterable
 */
function isAsyncIterable(value: unknown): value is AsyncIterable<string> {
  return (
    value !== null &&
    typeof value === 'object' &&
    Symbol.asyncIterator in value
  );
}

/**
 * Generate a unique message ID
 */
function generateMessageId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * ChatInterface component for text-based interaction with voice agent
 *
 * Provides a full-featured chat interface with:
 * - Message history display with user/assistant distinction
 * - Real-time streaming response support
 * - Copy message functionality
 * - Auto-scroll to latest messages
 * - Clear chat history
 * - Keyboard navigation support
 *
 * @example
 * ```tsx
 * <ChatInterface
 *   userId="user-123"
 *   onSendMessage={async (input, history) => {
 *     // Call your AI backend
 *     const response = await callAI(input, history);
 *     return response;
 *   }}
 *   placeholder="Ask me anything..."
 * />
 * ```
 */
const ChatInterface: React.FC<ChatInterfaceProps> = ({
  userId = 'default-user',
  onSendMessage,
  onSaveMessage,
  onLoadHistory,
  onClearHistory,
  placeholder = 'Type a message...',
  welcomeMessage,
  loading = false,
  className = '',
  maxHeight = '600px',
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

  // Refs
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  /**
   * Load message history on mount
   */
  useEffect(() => {
    const loadHistory = async () => {
      try {
        if (onLoadHistory) {
          const historyMessages = await onLoadHistory(userId);
          if (historyMessages && historyMessages.length > 0) {
            setMessages(historyMessages);
          }
        }
      } catch {
        // Failed to load history, start fresh
      }
    };
    loadHistory();
  }, [onLoadHistory, userId]);

  /**
   * Auto-scroll to bottom when new messages arrive
   */
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
      setShowScrollButton(false);
    }
  }, [messages]);

  /**
   * Track scroll position to show/hide scroll button
   */
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      setShowScrollButton(scrollTop + clientHeight < scrollHeight - 100);
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  /**
   * Scroll to bottom of messages
   */
  const scrollToBottom = useCallback(() => {
    messagesContainerRef.current?.scrollTo({
      top: messagesContainerRef.current.scrollHeight,
      behavior: 'smooth',
    });
    setShowScrollButton(false);
  }, []);

  /**
   * Copy message content to clipboard
   */
  const handleCopy = useCallback(async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch {
      // Failed to copy
    }
  }, []);

  /**
   * Send a message and handle response
   */
  const sendMessage = useCallback(async () => {
    if (!input.trim() || isTyping) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
      id: generateMessageId(),
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput('');
    setIsTyping(true);

    // Focus back on input
    inputRef.current?.focus();

    try {
      if (onSendMessage) {
        // Add empty assistant message for streaming
        const assistantMessageId = generateMessageId();
        setMessages([
          ...updatedMessages,
          { role: 'assistant', content: '', timestamp: new Date(), id: assistantMessageId },
        ]);

        const response = onSendMessage(input.trim(), updatedMessages);

        if (isAsyncIterable(response)) {
          // Handle streaming response
          let assistantContent = '';
          for await (const chunk of response) {
            assistantContent += chunk;
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                role: 'assistant',
                content: assistantContent,
                timestamp: new Date(),
                id: assistantMessageId,
              };
              return updated;
            });
          }

          const finalMessages: ChatMessage[] = [
            ...updatedMessages,
            { role: 'assistant', content: assistantContent, timestamp: new Date(), id: assistantMessageId },
          ];
          onSaveMessage?.(userId, finalMessages);
        } else {
          // Handle promise response
          const assistantResponse = await response;
          const finalMessages: ChatMessage[] = [
            ...updatedMessages,
            { role: 'assistant', content: assistantResponse, timestamp: new Date(), id: assistantMessageId },
          ];
          setMessages(finalMessages);
          onSaveMessage?.(userId, finalMessages);
        }
      } else {
        // No message handler, show demo response
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: "I'm a demo assistant. Connect me to your AI backend using the `onSendMessage` prop!",
          timestamp: new Date(),
          id: generateMessageId(),
        };
        const finalMessages = [...updatedMessages, assistantMessage];
        setMessages(finalMessages);
      }
    } catch {
      // Handle error
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: "I'm sorry, something went wrong. Please try again.",
        timestamp: new Date(),
        id: generateMessageId(),
      };
      setMessages([...updatedMessages, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  }, [input, isTyping, messages, onSendMessage, onSaveMessage, userId]);

  /**
   * Clear chat history
   */
  const clearChat = useCallback(() => {
    try {
      if (onClearHistory) {
        onClearHistory(userId);
      }
      setMessages([]);
    } catch {
      // Failed to clear history
    }
  }, [onClearHistory, userId]);

  /**
   * Handle input change with auto-resize
   */
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);

    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, []);

  /**
   * Handle keyboard events for sending messages
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    },
    [sendMessage]
  );

  if (loading) {
    return (
      <div className={`card overflow-hidden ${className}`} style={{ maxHeight }}>
        <ChatSkeleton />
      </div>
    );
  }

  return (
    <div
      className={`card flex flex-col overflow-hidden ${className}`}
      style={{ maxHeight }}
      role="region"
      aria-label="Chat interface"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-brand/10 rounded-full">
            <BotIcon className="h-5 w-5 text-brand" />
          </div>
          <span className="font-medium text-foreground">AI Assistant</span>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={clearChat}
            disabled={isTyping}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Clear chat history"
            title="Clear chat"
          >
            <ClearIcon className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Messages area */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
      >
        {messages.length === 0 ? (
          <WelcomeMessage message={welcomeMessage} />
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id || `${msg.role}-${msg.timestamp?.getTime()}`}
              className={`flex items-start gap-3 ${
                msg.role === 'user' ? 'flex-row-reverse' : ''
              }`}
            >
              {/* Avatar */}
              <div
                className={`flex-shrink-0 p-2 rounded-full ${
                  msg.role === 'user'
                    ? 'bg-brand text-white'
                    : 'bg-muted text-muted-foreground'
                }`}
              >
                {msg.role === 'user' ? (
                  <UserIcon className="h-4 w-4" />
                ) : (
                  <BotIcon className="h-4 w-4" />
                )}
              </div>

              {/* Message content */}
              <div
                className={`group relative max-w-[80%] px-4 py-3 rounded-2xl ${
                  msg.role === 'user'
                    ? 'bg-brand text-white rounded-br-md'
                    : 'bg-muted text-foreground rounded-bl-md'
                }`}
              >
                <div className="whitespace-pre-wrap break-words">{msg.content}</div>

                {/* Copy button for assistant messages */}
                {msg.role === 'assistant' && msg.content && (
                  <button
                    type="button"
                    onClick={() => handleCopy(msg.id || '', msg.content)}
                    className="absolute -bottom-1 -right-1 p-1.5 bg-background border border-border rounded-md shadow-sm opacity-0 group-hover:opacity-100 transition-opacity hover:bg-muted"
                    aria-label={copiedMessageId === msg.id ? 'Copied!' : 'Copy message'}
                    title={copiedMessageId === msg.id ? 'Copied!' : 'Copy'}
                  >
                    {copiedMessageId === msg.id ? (
                      <CheckIcon className="h-3 w-3 text-green-500" />
                    ) : (
                      <CopyIcon className="h-3 w-3 text-muted-foreground" />
                    )}
                  </button>
                )}
              </div>
            </div>
          ))
        )}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 p-2 rounded-full bg-muted text-muted-foreground">
              <BotIcon className="h-4 w-4" />
            </div>
            <div className="bg-muted rounded-2xl rounded-bl-md">
              <TypingIndicator />
            </div>
          </div>
        )}
      </div>

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <button
          type="button"
          onClick={scrollToBottom}
          className="absolute bottom-24 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-background border border-border rounded-full shadow-lg hover:bg-muted transition-colors flex items-center gap-1.5 text-sm text-muted-foreground"
          aria-label="Scroll to bottom"
        >
          <ArrowDownIcon className="h-4 w-4" />
          <span>New messages</span>
        </button>
      )}

      {/* Input area */}
      <div className="p-4 border-t border-border">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={isTyping}
              rows={1}
              className="w-full px-4 py-3 pr-12 bg-muted border border-border rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Message input"
              style={{ maxHeight: '120px' }}
            />
          </div>
          <button
            type="button"
            onClick={sendMessage}
            disabled={isTyping || !input.trim()}
            className="flex-shrink-0 p-3 bg-brand text-white rounded-xl hover:bg-brand-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
            aria-label="Send message"
          >
            <SendIcon className="h-5 w-5" />
          </button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground text-center">
          Press Enter to send, Shift + Enter for new line
        </p>
      </div>
    </div>
  );
};

export default ChatInterface;
