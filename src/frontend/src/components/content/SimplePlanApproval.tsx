import React from 'react';
import { Button, Card, Title3, Body1, Spinner } from '@fluentui/react-components';
import { CheckmarkCircle20Regular, DismissCircle20Regular } from '@fluentui/react-icons';
import { MPlanData } from '../../models';
import '../../styles/SimplePlanApproval.css';

interface SimplePlanApprovalProps {
    planData: MPlanData | null;
    onApprove: () => void;
    onReject: () => void;
    processing: boolean;
}

const SimplePlanApproval: React.FC<SimplePlanApprovalProps> = ({
    planData,
    onApprove,
    onReject,
    processing
}) => {
    if (!planData) return null;

    return (
        <Card className="simple-plan-approval">
            <div className="simple-plan-approval__header">
                <Title3>Here's what I'll do:</Title3>
            </div>
            
            <div className="simple-plan-approval__content">
                {planData.steps && planData.steps.length > 0 ? (
                    <ul className="simple-plan-approval__task-list">
                        {planData.steps.map((step, index) => (
                            <li key={step.id || index}>
                                <Body1>{step.cleanAction || step.action}</Body1>
                            </li>
                        ))}
                    </ul>
                ) : planData.context?.task ? (
                    <Body1>{planData.context.task}</Body1>
                ) : (
                    <Body1>{planData.user_request || 'Execute your request'}</Body1>
                )}
            </div>

            <div className="simple-plan-approval__actions">
                {processing ? (
                    <Spinner label="Processing..." />
                ) : (
                    <>
                        <Button
                            appearance="primary"
                            icon={<CheckmarkCircle20Regular />}
                            onClick={onApprove}
                            size="large"
                        >
                            Approve & Start
                        </Button>
                        <Button
                            appearance="secondary"
                            icon={<DismissCircle20Regular />}
                            onClick={onReject}
                            size="large"
                        >
                            Cancel
                        </Button>
                    </>
                )}
            </div>
        </Card>
    );
};

export default SimplePlanApproval;

