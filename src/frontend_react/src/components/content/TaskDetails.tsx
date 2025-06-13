// TaskDetails.tsx - Merged TSX + Styles

import { TaskDetailsProps } from "@/models";
import {
    Subtitle1,
    Text,
    Divider,
    Avatar,
    Checkbox,
    Body1,
    Body1Strong,
    Caption1,
} from "@fluentui/react-components";
import {
    Add20Regular,
    CheckmarkCircle20Regular,
    Dismiss20Regular,
    CircleHalfFill20Regular,
    CheckboxChecked20Regular,
    DismissSquare20Regular,
} from "@fluentui/react-icons";
import React from "react";
import { TaskService } from "@/services";
import PanelRightToolbar from "@/coral/components/Panels/PanelRightToolbar";
import "../../styles/TaskDetails.css";

const TaskDetails: React.FC<TaskDetailsProps> = ({
    planData,
    loading,
    OnApproveStep,
    OnRejectStep,
}) => {
    const completedCount = planData?.plan.completed || 0;
    const total = planData?.plan.total_steps || 1;
    const subTasks = planData.steps || [];
    const progress = completedCount / total;
    const agents = planData?.agents || [];

    const renderStatusIcon = (status: string) => {
        switch (status) {
            case "completed":
            case 'accepted':
                return (<CheckmarkCircle20Regular className="status-icon-completed" />
                );
            case "planned":
                return (<CircleHalfFill20Regular className="status-icon-planned" />
                );
            case "rejected":
                return (<Dismiss20Regular className="status-icon-rejected" />
                );
            default:
                return null;
        }
    }; return (
        <div className="task-details-container">
            <PanelRightToolbar panelTitle="Progress"></PanelRightToolbar>
            <div className="task-details-section">
                <div className="task-details-progress-header">
                    <div className="task-details-progress-card">
                        <div className="task-details-progress-icon">
                            <svg width="56" height="56" viewBox="0 0 56 56">
                                <circle
                                    cx="28"
                                    cy="28"
                                    r="24"
                                    fill="none"
                                    stroke="var(--colorNeutralBackground1)"
                                    strokeWidth="8"
                                />
                                <circle
                                    cx="28"
                                    cy="28"
                                    r="24"
                                    fill="none"
                                    stroke="var(--colorPaletteSeafoamBorderActive)"
                                    strokeWidth="8"
                                    strokeDasharray={`${progress * 150.8} 150.8`}
                                    strokeDashoffset="0"
                                    strokeLinecap="round"
                                    transform="rotate(-90 28 28)"
                                />
                            </svg>
                        </div>
                        <div>
                            <Body1Strong>{planData.plan.initial_goal}</Body1Strong>
                            <br />
                            <Text size={200}>
                                {planData.plan.completed} of {total} completed
                            </Text>
                        </div>
                    </div>
                </div>

                <div className="task-details-subtask-list">
                    {subTasks.map((subtask) => {
                        const { description, functionOrDetails } = TaskService.splitSubtaskAction(
                            subtask.action
                        );
                        const canInteract = planData.enableStepButtons;

                        return (<div key={subtask.id} className="task-details-subtask-item">
                            <div className="task-details-status-icon">
                                {renderStatusIcon(subtask.human_approval_status || subtask.status)}
                            </div>
                            <div className="task-details-subtask-content">
                                <span className={`task-details-subtask-description ${subtask.human_approval_status === "rejected" ? "strikethrough" : ""}`}>
                                    {description} {functionOrDetails && <Caption1>{functionOrDetails}</Caption1>}
                                </span>
                                <div className="task-details-action-buttons">
                                    {(subtask.human_approval_status !== "accepted" && subtask.human_approval_status !== "rejected") && (
                                        <>
                                            <CheckboxChecked20Regular
                                                onClick={
                                                    canInteract ? () => OnApproveStep(subtask) : undefined
                                                }
                                                className={canInteract ? "task-details-action-button" : "task-details-action-button-disabled"}
                                            />
                                            <DismissSquare20Regular
                                                onClick={
                                                    canInteract ? () => OnRejectStep(subtask) : undefined
                                                }
                                                className={canInteract ? "task-details-action-button" : "task-details-action-button-disabled"}
                                            />
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
                            <Avatar name={agent} size={32} badge={{ status: "available" }} />
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
