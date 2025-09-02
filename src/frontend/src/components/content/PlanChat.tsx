import { useEffect, useRef, useState, useCallback } from "react";
import {  DiamondRegular, CheckmarkCircleRegular, ClockRegular, ErrorCircleRegular, } from "@fluentui/react-icons";
import { Body1, Button, Spinner, Tag, ToolbarDivider} from "@fluentui/react-components";
import HeaderTools from "@/coral/components/Header/HeaderTools";
import { Copy, Send } from "@/coral/imports/bundleicons";
import ChatInput from "@/coral/modules/ChatInput";
import remarkGfm from "remark-gfm";
import rehypePrism from "rehype-prism";
import { AgentType, ChatMessage, PlanChatProps, role } from "@/models";
import { StreamingPlanUpdate,  webSocketService  } from "@/services/WebSocketService";
import ReactMarkdown from "react-markdown";
import "../../styles/PlanChat.css";
import "../../styles/Chat.css";
import "../../styles/prism-material-oceanic.css";
import { TaskService } from "@/services/TaskService";
import InlineToaster from "../toast/InlineToaster";
import ContentNotFound from "../NotFound/ContentNotFound";


// Type guard to check if a message has streaming properties
const hasStreamingProperties = (msg: ChatMessage): msg is ChatMessage & { 
  streaming?: boolean; 
  status?: string; 
  message_type?: string;
  step_id?: string;
} => {
  return 'streaming' in msg || 'status' in msg || 'message_type' in msg;
};

interface GroupedMessage {
  id: string;
  agent_name: string;
  messages: StreamingPlanUpdate[];
  status: string;
  latest_timestamp: string;
  step_id?: string;
}

const PlanChat: React.FC<PlanChatProps> = ({
  planData,
  input,
  loading,
  setInput,
  submittingChatDisableInput,
  OnChatSubmit,
  streamingMessages = [],
  wsConnected = false,
}) => {
  const messages = planData?.messages || [];
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [inputHeight, setInputHeight] = useState(0);
  const [groupedStreamingMessages, setGroupedStreamingMessages] = useState<GroupedMessage[]>([]);

  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputContainerRef = useRef<HTMLDivElement>(null);

  // Helper function to normalize timestamp
  const normalizeTimestamp = (timestamp?: string | number): string => {
    if (!timestamp) return new Date().toISOString();
    if (typeof timestamp === 'number') {
      // Backend sends float timestamp, convert to ISO string
      return new Date(timestamp * 1000).toISOString();
    }
    return timestamp;
  };

  // Group streaming messages by agent 
  const groupStreamingMessages = useCallback((messages: StreamingPlanUpdate[]): GroupedMessage[] => {
    const groups: { [key: string]: GroupedMessage } = {};

    messages.forEach((msg) => {
        // Create a unique key for grouping (agent + step)
        const groupKey = `${msg.agent_name || 'system'}_${msg.step_id || 'general'}`;
        
        if (!groups[groupKey]) {
          groups[groupKey] = {
            id: groupKey,
            agent_name: msg.agent_name || 'BOT',
            messages: [],
            status: msg.status || 'in_progress',
            latest_timestamp: normalizeTimestamp(msg.timestamp),
            step_id: msg.step_id,
          };
        }

        groups[groupKey].messages.push(msg);
        
         // Update status to latest
        const msgTimestamp = normalizeTimestamp(msg.timestamp);
        const groupTimestamp = groups[groupKey].latest_timestamp;
        if (msgTimestamp > groupTimestamp) {
          groups[groupKey].status = msg.status || groups[groupKey].status;
          groups[groupKey].latest_timestamp = msgTimestamp;
        }
      });

      return Object.values(groups).sort((a, b) => 
        new Date(a.latest_timestamp).getTime() - new Date(b.latest_timestamp).getTime()
      );
    }, []);

    // Update grouped messages when streaming messages change
    useEffect(() => {
      if (streamingMessages.length > 0) {
        const grouped = groupStreamingMessages(streamingMessages);
        setGroupedStreamingMessages(grouped);
      } else {
        // Clear grouped messages when no streaming messages
        setGroupedStreamingMessages([]);
      }
    }, [streamingMessages, groupStreamingMessages]);

    // Auto-scroll behavior
    useEffect(() => {
      scrollToBottom();
    }, [messages, groupedStreamingMessages]);

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

    // Get status icon for streaming messages
    const getStatusIcon = (status: string) => {
      switch (status) {
        case 'completed':
          return <CheckmarkCircleRegular style={{ color: '#107c10' }} />;
        case 'error':
        case 'failed':
          return <ErrorCircleRegular style={{ color: '#d13438' }} />;
        case 'in_progress':
          return <Spinner size="extra-tiny" />;
        default:
          return <ClockRegular />;
      }
    };

      // Get message type display text
    const getMessageTypeText = (messageType?: string, status?: string) => {
      if (status === 'completed') return 'Completed';
      if (status === 'error' || status === 'failed') return 'Failed';
      
      switch (messageType) {
        case 'thinking':
          return 'Thinking...';
        case 'action':
          return 'Working...';
        case 'result':
          return 'Result';
        case 'clarification_needed':
          return 'Needs Input';
        case 'plan_approval_request':
          return 'Approval Required';
        default:
          return status === 'in_progress' ? 'In Progress' : 'Live';
      }
    };

    if (!planData && !loading) {
      return (
        <ContentNotFound subtitle="The requested page could not be found." />
      );
    }

  // Render a grouped streaming message
  const renderGroupedStreamingMessage = (group: GroupedMessage) => {
    const latestMessage = group.messages[group.messages.length - 1];
    const hasMultipleMessages = group.messages.length > 1;

    return (
      <div key={group.id} className="message assistant streaming-message">
        <div className="plan-chat-header">
          <div className="plan-chat-speaker">
            <Body1 className="speaker-name">
              {TaskService.cleanTextToSpaces(group.agent_name)}
            </Body1>
            <Tag
              size="extra-small"
              shape="rounded"
              appearance="brand"
              className="bot-tag"
            >
              BOT
            </Tag>
            <Tag
              size="extra-small"
              shape="rounded"
              appearance="outline"
              icon={getStatusIcon(group.status)}
            >
              {getMessageTypeText(latestMessage.message_type, group.status)}
            </Tag>
          </div>
        </div>

        <Body1>
          <div className="plan-chat-message-content">
            {hasMultipleMessages ? (
              // Show combined content for multiple messages
              <div>
                {group.messages.map((msg, idx) => (
                  <div key={idx} style={{ marginBottom: '8px' }}>
                    {msg.content && (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypePrism]}
                      >
                        {TaskService.cleanHRAgent(msg.content)}
                      </ReactMarkdown>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              // Single message content
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypePrism]}
              >
                {TaskService.cleanHRAgent(latestMessage.content || "") || ""}
              </ReactMarkdown>
            )}


            <div className="assistant-footer">
              <div className="assistant-actions">
                <div>
                  <Button
                    onClick={() =>
                      latestMessage.content &&
                      navigator.clipboard.writeText(latestMessage.content)
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
                  Live updates from agent
                </Tag>
              </div>
            </div>
          </div>
        </Body1>
      </div>
    );
  };

  // Combine regular messages and streaming messages for display
  // const allMessages = [
  //   ...messages,
  //   // Add streaming messages as regular chat messages for display
  //   ...groupedStreamingMessages.map(group => ({
  //     source: group.agent_name,
  //     content: group.messages.map(msg => msg.content).join('\n\n'),
  //     streaming: true,
  //     status: group.status,
  //     message_type: group.messages[group.messages.length - 1].message_type,
  //     step_id: group.step_id
  //   }))
  // ];

// Check if agents are actively working
const agentsWorking = streamingMessages.length > 0 && 
  groupedStreamingMessages.some(group => 
    group.status === 'in_progress' || 
    group.messages.some(msg => msg.status === 'in_progress')
  );

// Get the name of the currently working agent
const getWorkingAgentName = (): string | null => {
  if (!agentsWorking) return null;
  
  // Find the first agent that's currently in progress
  const workingGroup = groupedStreamingMessages.find(group => 
    group.status === 'in_progress' || 
    group.messages.some(msg => msg.status === 'in_progress')
  );
  
  return workingGroup ? workingGroup.agent_name : null;
};

const workingAgentName = getWorkingAgentName();

// Disable input when agents are working
const shouldDisableInput = !planData?.enableChat || submittingChatDisableInput || agentsWorking;

// Generate dynamic placeholder text
const getPlaceholderText = (): string => {
  if (workingAgentName) {
    return `${TaskService.cleanTextToSpaces(workingAgentName)} is working on your plan...`;
  }
  return "Add more info to this task...";
};

  console.log('PlanChat - streamingMessages:', streamingMessages);
  console.log('PlanChat - submittingChatDisableInput:', submittingChatDisableInput);
  console.log('PlanChat - shouldDisableInput:', shouldDisableInput);

  return (
    <div className="chat-container">
      <div className="messages" ref={messagesContainerRef}>
        {/* WebSocket Connection Status */}
        {wsConnected && (
          <div className="connection-status">
            <Tag
              appearance="filled"
              color="success"
              size="extra-small"
              icon={<DiamondRegular />}
            >
              Real-time updates active
            </Tag>
          </div>
        )}
        
        <div className="message-wrapper">
          {/* Render regular messages */}
          {messages.map((msg, index) => {
            const isHuman = msg.source === AgentType.HUMAN;

            return (
              <div
                key={`regular-${index}`}
                className={`message ${isHuman ? role.user : role.assistant} ${hasStreamingProperties(msg) && msg.streaming ? 'streaming-message' : ''}`}
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
                      {hasStreamingProperties(msg) && msg.streaming && (
                        <Tag
                          size="extra-small"
                          shape="rounded"
                          appearance="outline"
                          icon={<Spinner size="extra-tiny" />}
                        >
                          {msg.message_type === 'thinking' ? 'Thinking...' : 
                           msg.message_type === 'action' ? 'Acting...' : 
                           msg.status === 'in_progress' ? 'Working...' : 'Live'}
                        </Tag>
                      )}
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

          {/* Render streaming messages */}
          {groupedStreamingMessages.map(group => renderGroupedStreamingMessage(group))}
        </div>
      </div>

      {showScrollButton && (
        <Tag
          onClick={scrollToBottom}
          className="scroll-to-bottom plan-chat-scroll-button"
          shape="circular"
          style={{
            bottom: inputHeight,
            position: "absolute",
            right: 16,
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
            disabledChat={shouldDisableInput}
            placeholder={getPlaceholderText()}
          >
            <Button
              appearance="transparent"
              onClick={() => OnChatSubmit(input)}
              icon={<Send />}
              disabled={shouldDisableInput}
            />
          </ChatInput>
        </div>
      </div>
    </div>
  );
};

export default PlanChat;