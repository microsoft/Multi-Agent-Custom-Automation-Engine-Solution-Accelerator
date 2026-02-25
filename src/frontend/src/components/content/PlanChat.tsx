import React from "react";
import { PlanChatProps, MPlanData } from "../../models/plan";
import InlineToaster from "../toast/InlineToaster";
import { AgentMessageData } from "@/models";
import { UserPlanMessage } from "./streaming/StreamingUserPlanMessage";
import { PlanResponse } from "./streaming/StreamingPlanResponse";
import { ThinkingState, PlanExecutionMessage } from "./streaming/StreamingPlanState";
import ContentNotFound from "../NotFound/ContentNotFound";
import PlanChatBody from "./PlanChatBody";
import { AgentMessageList } from "./streaming/StreamingAgentMessage";
import StreamingBufferMessage from "./streaming/StreamingBufferMessage";

interface SimplifiedPlanChatProps extends PlanChatProps {
  onPlanReceived?: (planData: MPlanData) => void;
  initialTask?: string;
  planApprovalRequest: MPlanData | null;
  waitingForPlan: boolean;
  messagesContainerRef: React.RefObject<HTMLDivElement | null>;
  streamingMessageBuffer: string;
  showBufferingText: boolean;
  agentMessages: AgentMessageData[];
  showProcessingPlanSpinner: boolean;
  showApprovalButtons: boolean;
  handleApprovePlan: () => Promise<void>;
  handleRejectPlan: () => Promise<void>;
  processingApproval: boolean;

}

const PlanChat: React.FC<SimplifiedPlanChatProps> = React.memo(({
  planData,
  input,
  setInput,
  submittingChatDisableInput,
  OnChatSubmit,
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
        ref={messagesContainerRef as React.RefObject<HTMLDivElement>}
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
        <UserPlanMessage
          planApprovalRequest={planApprovalRequest}
          initialTask={initialTask}
          planData={planData}
        />

        {/* AI thinking state */}
        <ThinkingState waitingForPlan={waitingForPlan} />

        {/* Plan response with all information */}
        <PlanResponse
          planApprovalRequest={planApprovalRequest}
          handleApprovePlan={handleApprovePlan}
          handleRejectPlan={handleRejectPlan}
          processingApproval={processingApproval}
          showApprovalButtons={showApprovalButtons}
        />

        {/* Agent messages – each type handled by its own sub-component */}
        <AgentMessageList agentMessages={agentMessages} />

        {/* Plan execution spinner */}
        {showProcessingPlanSpinner && <PlanExecutionMessage />}

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
});
PlanChat.displayName = 'PlanChat';

export default PlanChat;