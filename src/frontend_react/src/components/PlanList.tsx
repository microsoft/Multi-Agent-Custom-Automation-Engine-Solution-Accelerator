import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Card,
    CardHeader,
    Text,
    Badge,
    Button
} from '@fluentui/react-components';
import {
    Eye24Regular,
    Calendar24Regular,
    CheckmarkCircle24Regular,
    ErrorCircle24Regular,
    Clock24Regular
} from '@fluentui/react-icons';
import { PlanWithSteps, PlanStatus } from '../models';
import { apiService } from '../api/apiService';
import '../styles/PlanList.css';

interface PlanListProps {
    /** Array of plans to display */
    plans: PlanWithSteps[];
    /** Optional loading state */
    loading?: boolean;
    /** Optional empty state message */
    emptyMessage?: string;
    /** Optional flag to show view button */
    showViewButton?: boolean;
}

/**
 * Component to display a list of plans in a grid layout
 */
const PlanList: React.FC<PlanListProps> = ({
    plans,
    loading = false,
    emptyMessage = "No plans found",
    showViewButton = true
}) => {
    const navigate = useNavigate();

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

    /**
     * Get status icon based on plan status
     */
    const getPlanStatusIcon = (status: PlanStatus): JSX.Element => {
        switch (status) {
            case PlanStatus.COMPLETED:
                return <CheckmarkCircle24Regular />;
            case PlanStatus.FAILED:
                return <ErrorCircle24Regular />;
            case PlanStatus.IN_PROGRESS:
                return <Clock24Regular />;
            default:
                return <Calendar24Regular />;
        }
    };

    /**
     * Format status text for display
     */
    const getStatusText = (status: PlanStatus): string => {
        return status.replace('_', ' ').toLowerCase();
    };

    /**
     * Navigate to plan details page
     */
    const handleViewPlan = (planId: string) => {
        navigate(`/plan/${planId}`);
    };

    /**
     * Format timestamp to readable date
     */
    const formatDate = (timestamp: string): string => {
        return new Date(timestamp).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    // Show empty state if no plans
    if (!loading && plans.length === 0) {
        return (
            <div className="plan-list-empty">
                <Card>
                    <div className="empty-content">
                        <Calendar24Regular className="empty-icon" />
                        <Text size={500} weight="semibold">
                            {emptyMessage}
                        </Text>
                    </div>
                </Card>
            </div>
        );
    }

    return (
        <div className="plan-list-container">
            <div className="plan-list-grid">
                {plans.map((plan) => {
                    const completionPercentage = apiService.getPlanCompletionPercentage(plan);
                    const stepsAwaitingFeedback = apiService.getStepsAwaitingFeedback(plan);

                    return (
                        <Card key={plan.id} className="plan-list-card">
                            <CardHeader
                                header={
                                    <div className="plan-card-header">
                                        <Text className="plan-goal" size={500} weight="semibold">
                                            {plan.initial_goal}
                                        </Text>
                                        <div className="plan-badges">
                                            <Badge
                                                className="status-badge"
                                                color={getPlanStatusColor(plan.overall_status)}
                                                appearance="filled"
                                                icon={getPlanStatusIcon(plan.overall_status)}
                                            >
                                                {getStatusText(plan.overall_status)}
                                            </Badge>
                                            {stepsAwaitingFeedback.length > 0 && (
                                                <Badge
                                                    className="feedback-badge"
                                                    color="warning"
                                                    appearance="filled"
                                                >
                                                    {stepsAwaitingFeedback.length} awaiting feedback
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                }
                            />

                            <div className="plan-card-content">
                                {plan.summary && (
                                    <Text className="plan-summary">
                                        {plan.summary}
                                    </Text>
                                )}

                                <div className="plan-progress">
                                    <div className="progress-info">
                                        <Text size={300}>
                                            Progress: {plan.completed} of {plan.total_steps} steps completed
                                        </Text>
                                        <Text size={300} weight="semibold">
                                            {completionPercentage}%
                                        </Text>
                                    </div>
                                    <div className="progress-bar">
                                        <div
                                            className="progress-fill"
                                            style={{ width: `${completionPercentage}%` }}
                                        />
                                    </div>
                                </div>

                                <div className="plan-metadata">
                                    <Text size={200} className="plan-session">
                                        Session: {plan.session_id}
                                    </Text>
                                    <Text size={200} className="plan-date">
                                        {formatDate(plan.timestamp)}
                                    </Text>
                                </div>

                                {showViewButton && (
                                    <div className="plan-actions">
                                        <Button
                                            appearance="primary"
                                            icon={<Eye24Regular />}
                                            onClick={() => handleViewPlan(plan.id)}
                                        >
                                            View Details
                                        </Button>
                                    </div>
                                )}
                            </div>
                        </Card>
                    );
                })}
            </div>
        </div>
    );
};

export default PlanList;
