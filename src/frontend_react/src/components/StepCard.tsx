import React from 'react';
import {
    Card,
    CardHeader,
    CardFooter,
    Text,
    Button,
    TextField,
    Badge,
    Divider
} from '@fluentui/react-components';
import {
    CheckmarkCircle24Regular,
    DismissCircle24Regular,
    Edit24Regular,
    ChatBubblesQuestionRegular
} from '@fluentui/react-icons';
import { Step, StepStatus, AgentType, HumanFeedbackStatus } from '../models';
import '../styles/StepCard.css';

interface StepCardProps {
    step: Step;
    onApprove: (stepId: string, feedback?: string) => void;
    onReject: (stepId: string, feedback: string, updatedAction?: string) => void;
}

/**
 * Component to display a single step card with action buttons
 */
const StepCard: React.FC<StepCardProps> = ({ step, onApprove, onReject }) => {
    const [showFeedback, setShowFeedback] = React.useState(false);
    const [feedback, setFeedback] = React.useState('');
    const [updatedAction, setUpdatedAction] = React.useState('');
    const [editingAction, setEditingAction] = React.useState(false);

    /**
     * Get badge color based on step status
     */
    const getStatusColor = (status: StepStatus): string => {
        switch (status) {
            case StepStatus.COMPLETED:
            case StepStatus.APPROVED:
                return 'success';
            case StepStatus.IN_PROGRESS:
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
    };

    /**
     * Get agent type display name
     */
    const getAgentName = (agent: AgentType): string => {
        switch (agent) {
            case AgentType.PLANNER:
                return 'Planner';
            case AgentType.COPILOT:
                return 'Copilot';
            case AgentType.RESEARCHER:
                return 'Researcher';
            case AgentType.EXECUTOR:
                return 'Executor';
            default:
                return agent;
        }
    };

    /**
     * Handle approve action
     */
    const handleApprove = () => {
        onApprove(step.id, feedback);
        setShowFeedback(false);
        setFeedback('');
    };

    /**
     * Handle reject action
     */
    const handleReject = () => {
        onReject(step.id, feedback, editingAction ? updatedAction : undefined);
        setShowFeedback(false);
        setFeedback('');
        setEditingAction(false);
        setUpdatedAction('');
    };

    /**
     * Toggle feedback section visibility
     */
    const toggleFeedback = () => {
        setShowFeedback(!showFeedback);
        if (!showFeedback) {
            setFeedback('');
            setEditingAction(false);
            setUpdatedAction('');
        }
    };

    /**
     * Toggle action editing
     */
    const toggleEditAction = () => {
        setEditingAction(!editingAction);
        if (!editingAction) {
            setUpdatedAction(step.action);
        }
    };

    return (
        <Card className="step-card">
            <CardHeader
                className="step-card-header"
                header={
                    <Text className="step-id">Step: {step.id}</Text>
                }
                description={
                    <div className="step-badges">
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
                }
            />
            <div className="step-card-content">
                <Text className="action-label" weight="semibold">Action:</Text>
                <Text className="action-text">{step.action}</Text>

                {step.agent_reply && (
                    <>
                        <Divider className="step-divider" />
                        <Text className="reply-label" weight="semibold">Agent Reply:</Text>
                        <Text className="reply-text">{step.agent_reply}</Text>
                    </>
                )}

                {step.human_feedback && (
                    <>
                        <Divider className="step-divider" />
                        <Text className="feedback-label" weight="semibold">Human Feedback:</Text>
                        <Text className="feedback-text">{step.human_feedback}</Text>
                    </>
                )}

                {(step.status === StepStatus.AWAITING_FEEDBACK &&
                    step.human_approval_status === HumanFeedbackStatus.REQUESTED) && (
                        <CardFooter className="step-card-footer">
                            <div className="action-buttons">
                                <Button
                                    appearance="primary"
                                    icon={<CheckmarkCircle24Regular />}
                                    onClick={toggleFeedback}
                                >
                                    Provide Feedback
                                </Button>
                            </div>
                        </CardFooter>
                    )}

                {showFeedback && (
                    <div className="feedback-section">
                        <TextField
                            className="feedback-input"
                            label="Your Feedback"
                            multiline
                            rows={3}
                            value={feedback}
                            onChange={(e, data) => setFeedback(data.value)}
                        />

                        <div className="feedback-actions">
                            <Button
                                appearance="transparent"
                                icon={<Edit24Regular />}
                                onClick={toggleEditAction}
                            >
                                {editingAction ? 'Cancel Edit' : 'Edit Action'}
                            </Button>

                            <Button
                                icon={<ChatBubblesQuestionRegular />}
                                onClick={() => setFeedback(prev =>
                                    prev + (prev ? '\n' : '') + 'Please clarify: '
                                )}
                            >
                                Request Clarification
                            </Button>
                        </div>

                        {editingAction && (
                            <TextField
                                className="action-input"
                                label="Updated Action"
                                multiline
                                rows={3}
                                value={updatedAction}
                                onChange={(e, data) => setUpdatedAction(data.value)}
                            />
                        )}

                        <div className="decision-buttons">
                            <Button
                                appearance="primary"
                                icon={<CheckmarkCircle24Regular />}
                                onClick={handleApprove}
                            >
                                Approve
                            </Button>
                            <Button
                                appearance="outline"
                                icon={<DismissCircle24Regular />}
                                onClick={handleReject}
                            >
                                Reject
                            </Button>
                        </div>
                    </div>
                )}
            </div>
        </Card>
    );
};

export default StepCard;
