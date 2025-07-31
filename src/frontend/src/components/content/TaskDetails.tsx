// TaskDetails.tsx - Merged TSX + Styles

import { HumanFeedbackStatus, Step as OriginalStep, TaskDetailsProps } from "@/models";

// Extend Step to include _isActionLoading
type Step = OriginalStep & { _isActionLoading?: boolean };
import {
  Text,
  Avatar,
  Body1,
  Body1Strong,
  Caption1,
  Button,
  Tooltip,
} from "@fluentui/react-components";
import {
  Dismiss20Regular,
  CheckmarkCircle20Filled,
  DismissCircle20Filled,
  Checkmark20Regular,
  CircleHint20Filled,
} from "@fluentui/react-icons";
import React, { useState } from "react";
import { TaskService } from "@/services";
import PanelRightToolbar from "@/coral/components/Panels/PanelRightToolbar";
import "../../styles/TaskDetails.css";
import ProgressCircle from "@/coral/components/Progress/ProgressCircle";

// Helper functions for agent display
const getAgentColor = (agentName: string): string => {
  const cleanName = TaskService.cleanAgentName(agentName).toLowerCase();
  const colorMap: Record<string, string> = {
    'hr agent': '#4F46E5',       // Indigo
    'marketing agent': '#059669', // Emerald
    'finance agent': '#DC2626',   // Red
    'it agent': '#2563EB',        // Blue
    'operations agent': '#7C2D12', // Orange
    'sales agent': '#9333EA',     // Purple
    'legal agent': '#374151',     // Gray
    'project manager': '#059669', // Green
    'data analyst': '#DC2626',    // Rose
    'research agent': '#2563EB',  // Sky
    'customer service agent': '#EA580C', // Orange
    'supply chain agent': '#7C2D12',     // Amber
  };
  
  // Default color if agent not in map
  return colorMap[cleanName] || '#6B7280';
};

const getAgentInitials = (agentName: string): string => {
  const cleanName = TaskService.cleanAgentName(agentName);
  const words = cleanName.split(' ').filter(word => word.length > 0);
  
  if (words.length === 1) {
    return words[0].substring(0, 2).toUpperCase();
  } else if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  
  return 'AG'; // Default fallback
};

const getAgentRole = (agentName: string): string => {
  const cleanName = TaskService.cleanAgentName(agentName).toLowerCase();
  const roleMap: Record<string, string> = {
    'hr agent': 'Human Resources Specialist',
    'marketing agent': 'Marketing & Brand Strategy',
    'finance agent': 'Financial Analysis & Planning',
    'it agent': 'Information Technology Support',
    'operations agent': 'Operations & Process Management',
    'sales agent': 'Sales & Revenue Generation',
    'legal agent': 'Legal Affairs & Compliance',
    'project manager': 'Project Management & Coordination',
    'data analyst': 'Data Analysis & Insights',
    'research agent': 'Research & Market Intelligence',
    'customer service agent': 'Customer Support & Relations',
    'supply chain agent': 'Supply Chain & Logistics',
  };
  
  return roleMap[cleanName] || 'Specialized Assistant';
};

const TaskDetails: React.FC<TaskDetailsProps> = ({
  planData,
  loading,
  OnApproveStep,
}) => {
  // Handle null planData gracefully during streaming
  if (!planData) {
    return (
      <div className="task-details">
        <PanelRightToolbar panelTitle="Plan Details" />
        <div style={{ padding: "16px", textAlign: "center" }}>
          <Text>Loading plan details...</Text>
        </div>
      </div>
    );
  }

  const [steps, setSteps] = useState<Step[]>(planData.steps || []);
  const [completedCount, setCompletedCount] = useState(
    planData?.plan.completed || 0
  );
  const [total, setTotal] = useState(planData?.plan.total_steps || 1);
  const [progress, setProgress] = useState(
    (planData?.plan.completed || 0) / (planData?.plan.total_steps || 1)
  );
  const agents = planData?.agents || [];

  React.useEffect(() => {
    // Initialize steps and counts from planData
    setSteps(planData.steps || []);
    setCompletedCount(planData?.plan.completed || 0);
    setTotal(planData?.plan.total_steps || 1);
    setProgress(
      (planData?.plan.completed || 0) / (planData?.plan.total_steps || 1)
    );
  }, [planData]);

  const renderStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
      case "accepted":
      case "approved": // Add approved status for green checkmark
        return <CheckmarkCircle20Filled className="status-icon-completed" />;

      case "rejected":
        return <DismissCircle20Filled className="status-icon-rejected" />;
      case "planned":
      default:
        return <CircleHint20Filled className="status-icon-planned" />;
    }
  };
  // Pre-step function for approval
  const preOnApproved = async (step: Step) => {
    try {
      // Update the specific step's human_approval_status
      const updatedStep = {
        ...step,
        human_approval_status: "accepted" as HumanFeedbackStatus,
      };
      // Then call the main approval function
      // This could be your existing OnApproveStep function that handles API calls, etc.
      await OnApproveStep(updatedStep, total, completedCount + 1, true);
    } catch (error) {
      console.log("Error in pre-approval step:", error);
      throw error; // Re-throw to allow caller to handle
    }
  };

  // Pre-step function for rejection
  const preOnRejected = async (step: Step) => {
    try {
      // Update the specific step's human_approval_status
      const updatedStep = {
        ...step,
        human_approval_status: "rejected" as HumanFeedbackStatus,
      };

      // Then call the main rejection function
      // This could be your existing OnRejectStep function that handles API calls, etc.
      await OnApproveStep(updatedStep, total, completedCount + 1, false);
    } catch (error) {
      console.log("Error in pre-rejection step:", error);
      throw error; // Re-throw to allow caller to handle
    }
  };

  return (
    <div className="task-details-container">
      <PanelRightToolbar panelTitle="Progress"></PanelRightToolbar>
      <div className="task-details-section">
        <div className="task-details-progress-header">
          <div className="task-details-progress-card">
            <div className="task-details-progress-icon">
              <div className="task-details-progress-icon">
                <ProgressCircle progress={progress} />
              </div>
            </div>
            <div>
              <Tooltip content={planData.plan.initial_goal} relationship={"label"}>
                <Body1Strong
                  className="goal-text"
                >
                  {planData.plan.initial_goal}
                </Body1Strong>
              </Tooltip>
              <br />
              <Text size={200}>
                {completedCount} of {total} completed
              </Text>
            </div>
          </div>
        </div>

        <div className="task-details-subtask-list">
          {steps.map((step) => {
            const { description, functionOrDetails } =
              TaskService.splitSubtaskAction(step.action);
            const canInteract = planData.enableStepButtons;

            return (
              <div key={step.id} className="task-details-subtask-item">
                <div className="task-details-status-icon">
                  {renderStatusIcon(step.human_approval_status || step.status)}
                </div>
                <div className="task-details-subtask-content">
                  <Body1
                    className={`task-details-subtask-description ${step.human_approval_status === "rejected"
                      ? "strikethrough"
                      : ""
                      }`}
                  >
                    {description}{" "}
                    {functionOrDetails && (
                      <Caption1>{functionOrDetails}</Caption1>
                    )}
                  </Body1>
                  
                  {/* Show approval status feedback */}
                  {step._isActionLoading && (
                    <div style={{ 
                      marginTop: '8px',
                      padding: '6px 12px',
                      backgroundColor: '#FEF3C7',
                      border: '1px solid #F59E0B',
                      borderRadius: '6px',
                      fontSize: '12px',
                      color: '#D97706',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}>
                      <span>🔄</span>
                      <span>Approving task...</span>
                    </div>
                  )}
                  
                  {step.human_approval_status === "rejected" && (
                    <div style={{ 
                      marginTop: '8px',
                      padding: '6px 12px',
                      backgroundColor: '#FEE2E2',
                      border: '1px solid #EF4444',
                      borderRadius: '6px',
                      fontSize: '12px',
                      color: '#DC2626',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}>
                      <span>❌</span>
                      <span>Task rejected</span>
                    </div>
                  )}
                    <div className="task-details-action-buttons">
                    {step.human_approval_status !== "accepted" &&
                      step.human_approval_status !== "rejected" && 
                      step.status !== "approved" && 
                      step.status !== "rejected" && (
                      <>
                        <Tooltip relationship="label" content={canInteract ? "Approve" : "Step approval is currently disabled. Complete any clarification requests or ongoing approvals first."}>
                        <Button
                          icon={<Checkmark20Regular />}
                          appearance="subtle"
                          onClick={
                          canInteract
                            ? async (e) => {
                              // Disable buttons for this step
                              setSteps((prev) =>
                              prev.map((s) =>
                                s.id === step.id
                                ? { ...s, _isActionLoading: true }
                                : s
                              )
                              );
                              try {
                              await preOnApproved(step);
                              } finally {
                              // Remove loading state after API call
                              setSteps((prev) =>
                                prev.map((s) =>
                                s.id === step.id
                                  ? { ...s, _isActionLoading: false }
                                  : s
                                )
                              );
                              }
                            }
                            : undefined
                          }
                          disabled={
                          !canInteract ||
                          !!step._isActionLoading
                          }
                          className={
                          canInteract
                            ? "task-details-action-button"
                            : "task-details-action-button-disabled"
                          }
                        />
                        </Tooltip>

                        <Tooltip relationship="label" content={canInteract ? "Reject" : "Step approval is currently disabled. Complete any clarification requests or ongoing approvals first."}>
                        <Button
                          icon={<Dismiss20Regular />}
                          appearance="subtle"
                          onClick={
                          canInteract
                            ? async (e) => {
                              setSteps((prev) =>
                              prev.map((s) =>
                                s.id === step.id
                                ? { ...s, _isActionLoading: true }
                                : s
                              )
                              );
                              try {
                              await preOnRejected(step);
                              } finally {
                              setSteps((prev) =>
                                prev.map((s) =>
                                s.id === step.id
                                  ? { ...s, _isActionLoading: false }
                                  : s
                                )
                              );
                              }
                            }
                            : undefined
                          }
                          disabled={
                          !canInteract ||
                          !!step._isActionLoading
                          }
                          className={
                          canInteract
                            ? "task-details-action-button"
                            : "task-details-action-button-disabled"
                          }
                        />
                        </Tooltip>
                      </>
                      )}
                    </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="task-details-agents-container">
        <div className="task-details-agents-header">
          <Body1Strong>AI Agents Assigned</Body1Strong>
          <Caption1 style={{ color: '#666', marginTop: '4px' }}>
            {agents.length} agent{agents.length !== 1 ? 's' : ''} will work on this plan
          </Caption1>
        </div>
        <div className="task-details-agents-list">
          {agents.map((agent, index) => {
            const cleanAgentName = TaskService.cleanAgentName(agent);
            const agentColor = getAgentColor(agent);
            return (
              <div key={agent} className="task-details-agent-card" style={{
                borderLeft: `3px solid ${agentColor}`,
                backgroundColor: `${agentColor}08`,
                marginBottom: '8px'
              }}>
                <div style={{ 
                  width: '32px', 
                  height: '32px', 
                  borderRadius: '50%', 
                  backgroundColor: agentColor,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontWeight: 'bold',
                  fontSize: '14px'
                }}>
                  {getAgentInitials(cleanAgentName)}
                </div>
                <div className="task-details-agent-details">
                  <span className="task-details-agent-name" style={{ 
                    fontWeight: '600', 
                    color: agentColor,
                    display: 'block'
                  }}>
                    {cleanAgentName}
                  </span>
                  <Caption1 style={{ color: '#666', fontSize: '11px' }}>
                    {getAgentRole(agent)}
                  </Caption1>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default TaskDetails;
