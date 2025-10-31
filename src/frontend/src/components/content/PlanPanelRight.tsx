import React from "react";
import {
  Body1,
} from "@fluentui/react-components";
import {
  ArrowTurnDownRightRegular,
} from "@fluentui/react-icons";
import { MPlanData, PlanDetailsProps } from "../../models";
import { getAgentIcon, getAgentDisplayNameWithSuffix } from '../../utils/agentIconUtils';
import ContentNotFound from "../NotFound/ContentNotFound";
import "../../styles/planpanelright.css";


const PlanPanelRight: React.FC<PlanDetailsProps> = ({
  planData,
  loading,
  planApprovalRequest
}) => {

  if (!planData && !loading) {
    return <ContentNotFound subtitle="The requested page could not be found." />;
  }

  if (!planApprovalRequest) {
    return (
      <div className="plan-panel-right__no-data">
        No plan available
      </div>
    );
  }

  // Extract plan steps from the planApprovalRequest
  const extractPlanSteps = () => {
    if (!planApprovalRequest.steps || planApprovalRequest.steps.length === 0) {
      return [];
    }

    return planApprovalRequest.steps.map((step, index) => {
      const action = step.action || step.cleanAction || '';
      const isHeading = action.trim().endsWith(':');

      return {
        text: action.trim(),
        isHeading,
        key: `${index}-${action.substring(0, 20)}`
      };
    }).filter(step => step.text.length > 0);
  };

  // Render Plan Section
  const renderPlanSection = () => {
    const planSteps = extractPlanSteps();

    return (
      <div className="plan-section">
        <Body1 className="plan-section__title">
          Plan Overview
        </Body1>

        {planSteps.length === 0 ? (
          <div className="plan-section__empty">
            Plan is being generated...
          </div>
        ) : (
          <div className="plan-steps">
            {planSteps.map((step, index) => (
              <div key={step.key} className="plan-step">
                {step.isHeading ? (
                  // Heading - larger text, bold
                  <Body1 className="plan-step__heading">
                    {step.text}
                  </Body1>
                ) : (
                  // Sub-step - with arrow
                  <div className="plan-step__content">
                    <ArrowTurnDownRightRegular className="plan-step__arrow" />
                    <Body1 className="plan-step__text">
                      {step.text}
                    </Body1>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // Render Agents Section
  const renderAgentsSection = () => {
    const agents = planApprovalRequest?.team || [];

    return (
      <div className="agents-section">
        <Body1 className="agents-section__title">
          Agent Team
        </Body1>

        {agents.length === 0 ? (
          <div className="agents-section__empty">
            No agents assigned yet...
          </div>
        ) : (
          <div className="agents-list">
            {agents.map((agentName, index) => (
              <div key={`${agentName}-${index}`} className="agent-item">
                {/* Agent Icon */}
                <div className="agent-item__icon">
                  {getAgentIcon(agentName, planData, planApprovalRequest)}
                </div>

                {/* Agent Info - just name */}
                <div className="agent-item__info">
                  <Body1 className="agent-item__name">
                    {getAgentDisplayNameWithSuffix(agentName)}
                  </Body1>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // Main render
  return (
    <div className="plan-panel-right">
      {/* Plan section on top */}
      {renderPlanSection()}

      {/* Agents section below with line demarcation */}
      {renderAgentsSection()}
    </div>
  );
};

export default PlanPanelRight;