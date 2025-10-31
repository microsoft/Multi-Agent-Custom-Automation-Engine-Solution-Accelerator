import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  Button,
  Body1,
  Spinner,
  Tag,
  Textarea,
} from "@fluentui/react-components";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  CheckmarkRegular,
  DismissRegular,
  SendRegular,
  PersonRegular,
  BotRegular,
} from "@fluentui/react-icons";
import { PlanChatProps, MPlanData } from "../../models/plan";
import webSocketService from "../../services/WebSocketService";
import { PlanDataService } from "../../services/PlanDataService";
import { apiService } from "../../api/apiService";
import { useNavigate } from "react-router-dom";
import ChatInput from "../../coral/modules/ChatInput";
import InlineToaster, {
  useInlineToaster,
} from "../toast/InlineToaster";
import { AgentMessageData, WebsocketMessageType } from "@/models";
import getUserPlan from "./streaming/StreamingUserPlan";
import renderUserPlanMessage from "./streaming/StreamingUserPlanMessage";
import renderPlanResponse from "./streaming/StreamingPlanResponse";
import { renderPlanExecutionMessage, renderThinkingState } from "./streaming/StreamingPlanState";
import ContentNotFound from "../NotFound/ContentNotFound";
import PlanChatBody from "./PlanChatBody";
import renderAgentMessages from "./streaming/StreamingAgentMessage";
import StreamingBufferMessage from "./streaming/StreamingBufferMessage";

interface SimplifiedPlanChatProps extends PlanChatProps {
  onPlanReceived?: (planData: MPlanData) => void;
  initialTask?: string;
  planApprovalRequest: MPlanData | null;
  waitingForPlan: boolean;
  messagesContainerRef: React.RefObject<HTMLDivElement>;
  streamingMessageBuffer: string;
  showBufferingText: boolean;
  agentMessages: AgentMessageData[];
  showProcessingPlanSpinner: boolean;
  showApprovalButtons: boolean;
  handleApprovePlan: () => Promise<void>;
  handleRejectPlan: () => Promise<void>;
  processingApproval: boolean;

}

const PlanChat: React.FC<SimplifiedPlanChatProps> = ({
  planData,
  input,
  setInput,
  submittingChatDisableInput,
  OnChatSubmit,
  onPlanApproval,
  onPlanReceived,
  initialTask,
  planApprovalRequest,
  waitingForPlan,
  messagesContainerRef,
  streamingMessageBuffer,
  showBufferingText,
  agentMessages,
  showProcessingPlanSpinner,
  showApprovalButtons,
  handleApprovePlan,
  handleRejectPlan,
  processingApproval
}) => {
  // States

  if (!planData)
    return (
      <ContentNotFound subtitle="The requested page could not be found." />
    );
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',

    }}>
      {/* Messages Container */}
      <InlineToaster />
      <div
        ref={messagesContainerRef}
        style={{
          flex: 1,
          overflow: 'auto',
          padding: '32px 0',
          maxWidth: '800px',
          margin: '0 auto',
          width: '100%'
        }}
      >
        {/* User plan message */}
        {renderUserPlanMessage(planApprovalRequest, initialTask, planData)}

        {/* AI thinking state */}
        {renderThinkingState(waitingForPlan)}

        {/* Plan response with all information */}
        {renderPlanResponse(planApprovalRequest, handleApprovePlan, handleRejectPlan, processingApproval, showApprovalButtons)}
        {renderAgentMessages(agentMessages)}

        {showProcessingPlanSpinner && renderPlanExecutionMessage()}
        {/* Streaming plan updates */}
        {showBufferingText && (
          <StreamingBufferMessage
            streamingMessageBuffer={streamingMessageBuffer}
            isStreaming={true}
          />
        )}
      </div>

      {/* Chat Input - only show if no plan is waiting for approval */}
      <PlanChatBody
        planData={planData}
        input={input}
        setInput={setInput}
        submittingChatDisableInput={submittingChatDisableInput}
        OnChatSubmit={OnChatSubmit}
        waitingForPlan={waitingForPlan}
        loading={false} />

    </div>
  );
};

export default PlanChat;