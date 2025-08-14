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

const TaskDetails: React.FC<TaskDetailsProps> = ({
  planData,
  loading,
  OnApproveStep,
}) => {
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
                    <div className="task-details-action-buttons">
                    {step.human_approval_status !== "accepted" &&
                      step.human_approval_status !== "rejected" && (
                      <>
                        <Tooltip relationship="label" content={canInteract ? "Approve" : "You must first provide feedback to the planner"}>
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

                        <Tooltip relationship="label" content={canInteract ? "Reject" : "You must first provide feedback to the planner"}>
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
          <Body1Strong>Agents</Body1Strong>
        </div>
        <div className="task-details-agents-list">
          {agents.map((agent) => (
            <div key={agent} className="task-details-agent-card">
              <Avatar name={agent} size={32} />
              <div className="task-details-agent-details">
                <span className="task-details-agent-name">
                  {TaskService.cleanTextToSpaces(agent)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TaskDetails;
