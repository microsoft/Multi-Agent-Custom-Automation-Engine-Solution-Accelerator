import HeaderTools from "@/coral/components/Header/HeaderTools";
import { Copy, Send } from "@/coral/imports/bundleicons";
import ChatInput from "@/coral/modules/ChatInput";
import remarkGfm from "remark-gfm";
import rehypePrism from "rehype-prism";
import { AgentType, ChatMessage, PlanChatProps, role } from "@/models";
import { StreamingPlanUpdate, webSocketService } from "@/services/WebSocketService";
import {
  Body1,
  Button,
  Spinner,
  Tag,
  ToolbarDivider,
} from "@fluentui/react-components";
import { DiamondRegular, HeartRegular, CheckmarkRegular, DismissRegular } from "@fluentui/react-icons";
import { useEffect, useRef, useState } from "react";

// Type guard to check if a message has streaming properties
const hasStreamingProperties = (msg: ChatMessage): msg is ChatMessage & { streaming?: boolean; status?: string; message_type?: string; } => {
  return 'streaming' in msg || 'status' in msg || 'message_type' in msg;
};
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
  streamingMessages = [],
  wsConnected = false,
}) => {
  const messages = planData?.messages || [];
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [inputHeight, setInputHeight] = useState(0);
  
  // WebSocket states for plan approval
  const [approvalWs, setApprovalWs] = useState<WebSocket | null>(null);
  const [pendingApproval, setPendingApproval] = useState<any>(null);
  const [approvalStatus, setApprovalStatus] = useState<'pending' | 'approved' | 'rejected' | null>(null);

  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputContainerRef = useRef<HTMLDivElement>(null);

  // Debug logging
  console.log('PlanChat - planData:', planData);
  console.log('PlanChat - messages:', messages);
  console.log('PlanChat - messages.length:', messages.length);

  // WebSocket connection for plan approval
  useEffect(() => {
    if (planData?.plan?.id) {
      connectToApprovalWebSocket(planData.plan.id);
    }
    
    return () => {
      if (approvalWs) {
        approvalWs.close();
      }
    };
  }, [planData?.plan?.id]);

  const connectToApprovalWebSocket = async (planId: string) => {
    try {
      console.log('Connecting to approval WebSocket for plan:', planId);
      
      const ws = await webSocketService.createApprovalWebSocket(planId);
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('Approval WebSocket message received:', message);
          
          if (message.type === 'plan_ready') {
            setPendingApproval(message.plan);
            setApprovalStatus('pending');
          } else if (message.type === 'ack') {
            console.log('Approval acknowledged:', message.message);
            setApprovalStatus(message.message === 'approved' ? 'approved' : 'rejected');
            // Clear pending approval after a delay
            setTimeout(() => {
              setPendingApproval(null);
              setApprovalStatus(null);
            }, 3000);
          }
        } catch (error) {
          console.error('Error parsing approval WebSocket message:', error);
        }
      };
      
      ws.onclose = () => {
        console.log('Approval WebSocket disconnected');
        setApprovalWs(null);
      };
      
      ws.onerror = (error) => {
        console.error('Approval WebSocket error:', error);
        setApprovalWs(null);
      };
      
      setApprovalWs(ws);
      
    } catch (error) {
      console.error('Failed to connect to approval WebSocket:', error);
    }
  };

  const handleApprove = () => {
    if (approvalWs && approvalWs.readyState === WebSocket.OPEN) {
      approvalWs.send(JSON.stringify({ type: 'approve' }));
      console.log('Approval sent');
    }
  };

  const handleReject = () => {
    if (approvalWs && approvalWs.readyState === WebSocket.OPEN) {
      approvalWs.send(JSON.stringify({ type: 'reject' }));
      console.log('Rejection sent');
    }
  };

  // Scroll to Bottom useEffect

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessages]);

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

  if (!planData)
    return (
      <ContentNotFound subtitle="The requested page could not be found." />
    );

  // If no messages exist, show the initial task as the first message
  const displayMessages = messages.length > 0 ? messages : [
    {
      source: AgentType.HUMAN,
      content: planData.plan?.initial_goal || "Task started",
      timestamp: planData.plan?.timestamp || new Date().toISOString()
    }
  ];

  // Merge streaming messages with existing messages
  const allMessages: ChatMessage[] = [...displayMessages];
  
  // Add streaming messages as assistant messages
  streamingMessages.forEach(streamMsg => {
    if (streamMsg.content) {
      allMessages.push({
        source: streamMsg.agent_name || 'AI Assistant',
        content: streamMsg.content,
        timestamp: new Date().toISOString(),
        streaming: true,
        status: streamMsg.status,
        message_type: streamMsg.message_type
      });
    }
  });

  console.log('PlanChat - all messages including streaming:', allMessages);

  return (
    <div className="chat-container">
      {/* Plan Approval Section */}
      {pendingApproval && (
        <div className="approval-section">
          <div style={{ marginBottom: '12px' }}>
            <Body1><strong>Plan Ready for Review</strong></Body1>
            <Body1>Please review and approve or reject the proposed plan.</Body1>
          </div>
          
          {approvalStatus === 'pending' && (
            <div className="approval-buttons">
              <Button 
                appearance="primary" 
                icon={<CheckmarkRegular />}
                onClick={handleApprove}
                className="approval-button-approve"
              >
                Approve Plan
              </Button>
              <Button 
                appearance="outline" 
                icon={<DismissRegular />}
                onClick={handleReject}
                className="approval-button-reject"
              >
                Reject Plan
              </Button>
              <Tag
                appearance="filled"
                color="brand"
                size="small"
                icon={<Spinner size="extra-tiny" />}
              >
                Awaiting Decision
              </Tag>
            </div>
          )}
          
          {approvalStatus === 'approved' && (
            <Tag
              appearance="filled"
              color="success"
              size="small"
              icon={<CheckmarkRegular />}
            >
              Plan Approved
            </Tag>
          )}
          
          {approvalStatus === 'rejected' && (
            <Tag
              appearance="filled"
              color="danger"
              size="small"
              icon={<DismissRegular />}
            >
              Plan Rejected
            </Tag>
          )}
        </div>
      )}
      
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
        
        {/* Approval WebSocket Status */}
        {approvalWs && (
          <div className="connection-status">
            <Tag
              appearance="filled"
              color="informative"
              size="extra-small"
              icon={<DiamondRegular />}
            >
              Plan approval ready
            </Tag>
          </div>
        )}
        
        <div className="message-wrapper">
          {allMessages.map((msg, index) => {
            const isHuman = msg.source === AgentType.HUMAN;

            return (
              <div
                key={index}
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
