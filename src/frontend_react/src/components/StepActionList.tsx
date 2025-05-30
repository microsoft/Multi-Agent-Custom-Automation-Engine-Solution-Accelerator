import React from 'react';
import {
    Card,
    CardHeader,
    Text,
    Button,
    Badge
} from '@fluentui/react-components';
import {
    CheckmarkCircle24Regular,
    DismissCircle24Regular,
    Clock24Regular
} from '@fluentui/react-icons';
import { Step, StepStatus, AgentType } from '../models';
import '../styles/StepActionList.css';

interface StepActionListProps {
    /** Array of steps to display */
    steps: Step[];
    /** Callback function when approve button is clicked */
    onApprove: (stepId: string) => void;
    /** Callback function when reject button is clicked */
    onReject: (stepId: string) => void;
    /** Optional loading state for actions */
    loading?: boolean;
    /** Optional flag to show only steps awaiting feedback */
    showOnlyAwaitingFeedback?: boolean;
    /** Optional empty state message */
    emptyMessage?: string;
}

/**
 * Simple component to display a list of steps with approve/reject actions
 */
const StepActionList: React.FC<StepActionListProps> = ({
    steps,
    onApprove,
    onReject,
    loading = false,
    showOnlyAwaitingFeedback = false,
    emptyMessage = "No steps found"
}) => {    /**
     * Get badge color based on step status
     */
    const getStatusColor = (status: StepStatus): "success" | "brand" | "danger" | "warning" | "informative" => {
        switch (status) {
            case StepStatus.COMPLETED:
            case StepStatus.APPROVED:
                return 'success';
            case StepStatus.ACTION_REQUESTED:
                return 'brand';
            case StepStatus.FAILED:
            case StepStatus.REJECTED:
                return 'danger';
            case StepStatus.AWAITING_FEEDBACK:
                return 'warning';
            default:
                return 'informative';
        }
    };

    /**
     * Get status text from enum
     */
    const getStatusText = (status: StepStatus): string => {
        return status.replace('_', ' ');
    };    /**
     * Get agent type display name
     */
    const getAgentName = (agent: AgentType): string => {
        switch (agent) {
            case AgentType.PLANNER:
                return 'Planner';
            case AgentType.HUMAN:
                return 'Human';
            case AgentType.HR:
                return 'HR';
            case AgentType.MARKETING:
                return 'Marketing';
            case AgentType.PROCUREMENT:
                return 'Procurement';
            case AgentType.PRODUCT:
                return 'Product';
            case AgentType.GENERIC:
                return 'Generic';
            case AgentType.TECH_SUPPORT:
                return 'Tech Support';
            case AgentType.GROUP_CHAT_MANAGER:
                return 'Group Chat Manager';
            default:
                return agent;
        }
    };

    /**
     * Handle approve action
     */
    const handleApprove = (stepId: string) => {
        if (!loading) {
            onApprove(stepId);
        }
    };

    /**
     * Handle reject action
     */
    const handleReject = (stepId: string) => {
        if (!loading) {
            onReject(stepId);
        }
    };

    // Filter steps if needed
    const filteredSteps = showOnlyAwaitingFeedback
        ? steps.filter(step => step.status === StepStatus.AWAITING_FEEDBACK)
        : steps;

    // Show empty state if no steps
    if (filteredSteps.length === 0) {
        return (
            <div className="step-action-list-empty">
                <Card>
                    <div className="empty-content">
                        <Clock24Regular className="empty-icon" />
                        <Text size={500} weight="semibold">
                            {emptyMessage}
                        </Text>
                    </div>
                </Card>
            </div>
        );
    }

    return (
        <div className="step-action-list-container">
            <div className="step-action-list">
                {filteredSteps.map((step) => (
                    <Card key={step.id} className="step-action-card">
                        <CardHeader
                            header={
                                <div className="step-action-header">
                                    <Text className="step-action-title" size={400} weight="semibold">
                                        Step {step.id}
                                    </Text>
                                    <div className="step-action-badges">
                                        <Badge
                                            className="status-badge"
                                            color={getStatusColor(step.status)}
                                            appearance="filled"
                                        >
                                            {getStatusText(step.status)}
                                        </Badge>
                                        <Badge
                                            className="agent-badge"
                                            appearance="tint"
                                        >
                                            {getAgentName(step.agent)}
                                        </Badge>
                                    </div>
                                </div>
                            }
                        />

                        <div className="step-action-content">
                            <Text className="step-action-label" weight="semibold">Action:</Text>
                            <Text className="step-action-text">{step.action}</Text>

                            {step.agent_reply && (
                                <>
                                    <Text className="step-reply-label" weight="semibold">Agent Reply:</Text>
                                    <Text className="step-reply-text">{step.agent_reply}</Text>
                                </>
                            )}

                            {step.human_feedback && (
                                <>
                                    <Text className="step-feedback-label" weight="semibold">Previous Feedback:</Text>
                                    <Text className="step-feedback-text">{step.human_feedback}</Text>
                                </>
                            )}

                            {step.status === StepStatus.AWAITING_FEEDBACK && (
                                <div className="step-action-buttons">
                                    <Button
                                        appearance="primary"
                                        icon={<CheckmarkCircle24Regular />}
                                        onClick={() => handleApprove(step.id)}
                                        disabled={loading}
                                    >
                                        Approve
                                    </Button>
                                    <Button
                                        appearance="outline"
                                        icon={<DismissCircle24Regular />}
                                        onClick={() => handleReject(step.id)}
                                        disabled={loading}
                                    >
                                        Reject
                                    </Button>
                                </div>
                            )}
                        </div>
                    </Card>
                ))}
            </div>
        </div>
    );
};

export default StepActionList;
