import React from 'react';
import { Card, Title3, Body1, ProgressBar, Spinner } from '@fluentui/react-components';
import '../../styles/SimpleProgress.css';

interface SimpleProgressIndicatorProps {
    currentStep: number;
    totalSteps: number;
    message?: string;
}

const SimpleProgressIndicator: React.FC<SimpleProgressIndicatorProps> = ({
    currentStep,
    totalSteps,
    message = "Working on your request..."
}) => {
    const progress = totalSteps > 0 ? (currentStep / totalSteps) : 0;

    return (
        <Card className="simple-progress">
            <div className="simple-progress__content">
                <div className="simple-progress__spinner">
                    <Spinner size="large" />
                </div>
                <Title3>{message}</Title3>
                {totalSteps > 0 && (
                    <>
                        <Body1 className="simple-progress__step-text">
                            Step {currentStep} of {totalSteps} completed
                        </Body1>
                        <ProgressBar 
                            value={progress} 
                            max={1}
                            className="simple-progress__bar"
                        />
                    </>
                )}
            </div>
        </Card>
    );
};

export default SimpleProgressIndicator;



