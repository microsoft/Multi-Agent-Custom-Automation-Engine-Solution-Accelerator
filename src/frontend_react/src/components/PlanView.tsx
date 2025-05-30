import React from 'react';
import {
    Card,
    CardHeader,
    Text,
    Badge,
    Divider,
    Spinner,
    Alert
} from '@fluentui/react-components';
import {
    AlertCircle24Regular,
    CheckmarkCircle24Regular,
    ErrorCircle24Regular
} from '@fluentui/react-icons';
import { PlanStatus } from '../models';
import usePlan from '../hooks/usePlan';
import StepCard from './StepCard';
import '../styles/PlanView.css';

interface PlanViewProps {
    sessionId: string;
    planId: string;
}

/**
 * Component to display a plan and its steps using Fluent UI
 */
const PlanView: React.FC<PlanViewProps> = ({ sessionId, planId }) => {
    /**
     * Get badge color based on plan status
     */
    const getPlanStatusColor = (status: PlanStatus): string => {
        switch (status) {
            case PlanStatus.COMPLETED:
                return 'success';
            case PlanStatus.IN_PROGRESS:
                return 'brand';
            case PlanStatus.FAILED:
                return 'danger';
            default:
                return 'informative';
        }
    };

    // Use the custom hook to handle plan data
    const {
        plan,
        loading,
        error,
        fetchPlan,
        updateStepFeedback,
        getStepsAwaitingFeedback
    } = usePlan(sessionId, planId);

    // Handler for approving a step
    const handleApproveStep = (stepId: string, feedback?: string) => {
        updateStepFeedback(stepId, true, feedback);
    };

    // Handler for rejecting a step
    const handleRejectStep = (stepId: string, feedback: string, updatedAction?: string) => {
        updateStepFeedback(stepId, false, feedback, updatedAction);
    };

    // Display loading state
    if (loading && !plan) {
        return (
            <div className="plan-loading">
                <Spinner size="large" label="Loading plan data..." />
            </div>
        );
    }

    // Display error state
    if (error) {
        return (
            <div className="plan-error">
                <Alert
                    intent="error"
                    action={{
                        title: "Try Again",
                        onClick: fetchPlan
                    }}
                    icon={<ErrorCircle24Regular />}
                    title="Error Loading Plan"
                >
                    {error.message}
                </Alert>
            </div>
        );
    }

    // Display empty state if no plan found
    if (!plan) {
        return (
            <div className="plan-empty">
                <Alert
                    intent="warning"
                    icon={<AlertCircle24Regular />}
                    title="No Plan Found"
                >
                    No plan found with the provided ID. Please check the plan ID and try again.
                </Alert>
            </div>
        );
    }

    // Steps awaiting feedback
    const stepsAwaitingFeedback = getStepsAwaitingFeedback();

    return (
        <div className="plan-view-container">
            <div className="plan-header">
                <Text className="plan-title" size={700} weight="semibold">
                    Plan Details
                </Text>
                <Badge
                    className="plan-status-badge"
                    color={getPlanStatusColor(plan.overall_status)}
                    appearance="filled"
                >
                    {plan.overall_status.replace('_', ' ')}
                </Badge>
            </div>

            <Card className="plan-card">
                <CardHeader
                    header={
                        <Text className="plan-goal-label" weight="semibold">Goal</Text>
                    }
                />
                <div className="card-content">
                    <Text className="plan-goal-text">{plan.initial_goal}</Text>

                    {plan.summary && (
                        <>
                            <Divider className="plan-divider" />
                            <Text className="plan-summary-label" weight="semibold">Summary</Text>
                            <Text className="plan-summary-text">{plan.summary}</Text>
                        </>
                    )}

                    {plan.human_clarification_request && (
                        <>
                            <Divider className="plan-divider" />
                            <Text className="plan-clarification-label" weight="semibold">
                                Clarification Request
                            </Text>
                            <Text className="plan-clarification-text">
                                {plan.human_clarification_request}
                            </Text>
                        </>
                    )}

                    {plan.human_clarification_response && (
                        <>
                            <Divider className="plan-divider" />
                            <Text className="plan-response-label" weight="semibold">
                                Clarification Response
                            </Text>
                            <Text className="plan-response-text">
                                {plan.human_clarification_response}
                            </Text>
                        </>
                    )}

                    <div className="plan-progress">
                        <Text className="progress-text">
                            Progress: {plan.completed} of {plan.total_steps} steps completed
                        </Text>
                    </div>
                </div>
            </Card>

            <div className="steps-header">
                <Text className="steps-title" size={600} weight="semibold">
                    Steps
                </Text>
                {stepsAwaitingFeedback.length > 0 && (
                    <Badge
                        className="awaiting-badge"
                        color="warning"
                        appearance="filled"
                    >
                        {stepsAwaitingFeedback.length} Awaiting Feedback
                    </Badge>
                )}
            </div>

            <div className="steps-list">
                {plan.steps.map(step => (
                    <StepCard
                        key={step.id}
                        step={step}
                        onApprove={handleApproveStep}
                        onReject={handleRejectStep}
                    />
                ))}
            </div>
        </div>
    );
};

export default PlanView;
