/**
 * Example usage of the StepActionList component
 * 
 * This file demonstrates how to use the StepActionList component 
 * in different scenarios within your application.
 */

import React, { useState } from 'react';
import StepActionList from '../components/StepActionList';
import { Step, StepStatus, AgentType } from '../models';
import { apiService } from '../api/apiService';

/**
 * Example: Using StepActionList in a plan page
 */
const PlanPageExample: React.FC = () => {
    const [steps, setSteps] = useState<Step[]>([]);
    const [loading, setLoading] = useState(false);

    // Example: Handle approve action
    const handleApproveStep = async (stepId: string) => {
        setLoading(true);
        try {
            // Call your API service to approve the step
            await apiService.provideStepFeedback(
                stepId,
                'plan-id', // Replace with actual plan ID
                'session-id', // Replace with actual session ID
                true // approved = true
            );

            // Update the local state or refetch data
            // This is where you would update multiple components
            await refetchPlanData();
        } catch (error) {
            console.error('Failed to approve step:', error);
        } finally {
            setLoading(false);
        }
    };

    // Example: Handle reject action
    const handleRejectStep = async (stepId: string) => {
        setLoading(true);
        try {
            // Call your API service to reject the step
            await apiService.provideStepFeedback(
                stepId,
                'plan-id', // Replace with actual plan ID
                'session-id', // Replace with actual session ID
                false // approved = false
            );

            // Update the local state or refetch data
            // This is where you would update multiple components
            await refetchPlanData();
        } catch (error) {
            console.error('Failed to reject step:', error);
        } finally {
            setLoading(false);
        }
    };

    // Example: Refetch plan data to update all components
    const refetchPlanData = async () => {
        // This would trigger updates to:
        // - Plan status
        // - Progress bars
        // - Step counts
        // - Other plan-related components
        console.log('Refetching plan data to update all components');
    };

    return (
        <div>
            <h2>Plan Steps Requiring Action</h2>
            <StepActionList
                steps={steps}
                onApprove={handleApproveStep}
                onReject={handleRejectStep}
                loading={loading}
                showOnlyAwaitingFeedback={true}
                emptyMessage="No steps are currently awaiting your feedback"
            />
        </div>
    );
};

/**
 * Example: Using StepActionList for all steps (not just awaiting feedback)
 */
const AllStepsExample: React.FC = () => {
    const [steps, setSteps] = useState<Step[]>([]);

    const handleApprove = async (stepId: string) => {
        // Your approval logic here
        console.log('Approving step:', stepId);
    };

    const handleReject = async (stepId: string) => {
        // Your rejection logic here
        console.log('Rejecting step:', stepId);
    };

    return (
        <div>
            <h2>All Plan Steps</h2>
            <StepActionList
                steps={steps}
                onApprove={handleApprove}
                onReject={handleReject}
                showOnlyAwaitingFeedback={false} // Show all steps
                emptyMessage="No steps found for this plan"
            />
        </div>
    );
};

/**
 * Example: Integration with existing plan data
 */
const IntegratedExample: React.FC<{ planId: string; sessionId: string }> = ({
    planId,
    sessionId
}) => {
    const [steps, setSteps] = useState<Step[]>([]);
    const [loading, setLoading] = useState(false);

    // Example: Load steps from API
    React.useEffect(() => {
        const loadSteps = async () => {
            try {
                const planSteps = await apiService.getSteps(planId);
                setSteps(planSteps);
            } catch (error) {
                console.error('Failed to load steps:', error);
            }
        };

        loadSteps();
    }, [planId]);

    // Integrated action handlers that update multiple components
    const handleStepAction = async (stepId: string, approved: boolean) => {
        setLoading(true);
        try {
            await apiService.provideStepFeedback(stepId, planId, sessionId, approved);

            // Update local steps state
            setSteps(prevSteps =>
                prevSteps.map(step =>
                    step.id === stepId
                        ? { ...step, status: approved ? StepStatus.APPROVED : StepStatus.REJECTED }
                        : step
                )
            );

            // Trigger updates to other components
            // This could be through:
            // - Context updates
            // - Parent component callbacks
            // - Global state management
            // - Event emitters

        } catch (error) {
            console.error('Failed to update step:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <StepActionList
            steps={steps}
            onApprove={(stepId) => handleStepAction(stepId, true)}
            onReject={(stepId) => handleStepAction(stepId, false)}
            loading={loading}
            showOnlyAwaitingFeedback={true}
        />
    );
};

export { PlanPageExample, AllStepsExample, IntegratedExample };
