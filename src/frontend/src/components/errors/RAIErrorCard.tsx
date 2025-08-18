import React from 'react';
import {
    Text,
    Button,
    Card,
} from '@fluentui/react-components';
import {
    ShieldError24Filled,
    Warning20Regular,
    Lightbulb20Regular,
    Dismiss20Regular
} from '@fluentui/react-icons';
import './RAIErrorCard.css';

export interface RAIErrorData {
    error_type: string;
    message: string;
    description: string;
    suggestions: string[];
    user_action: string;
}

interface RAIErrorCardProps {
    error: RAIErrorData;
    onRetry?: () => void;
    onDismiss?: () => void;
    className?: string;
}

const RAIErrorCard: React.FC<RAIErrorCardProps> = ({
    error,
    onRetry,
    onDismiss,
    className = ''
}) => {
    return (
        <Card className={`rai-error-card ${className}`}>
            <div className="rai-error-header">
                <div className="rai-error-icon">
                    <ShieldError24Filled />
                </div>
                <div className="rai-error-title">
                    <Text size={500} weight="semibold">
                        {error.message}
                    </Text>
                    {onDismiss && (
                        <Button
                            appearance="subtle"
                            icon={<Dismiss20Regular />}
                            onClick={onDismiss}
                            className="rai-error-dismiss"
                            aria-label="Dismiss error"
                        />
                    )}
                </div>
            </div>

            <div className="rai-error-content">
                <div className="rai-error-description">
                    <Warning20Regular className="rai-warning-icon" />
                    <Text size={300}>
                        {error.description}
                    </Text>
                </div>

                {error.suggestions && error.suggestions.length > 0 && (
                    <div className="rai-error-suggestions">
                        <div className="rai-suggestions-header">
                            <Lightbulb20Regular className="rai-suggestion-icon" />
                            <Text size={300} weight="semibold">
                                Here's how to fix this:
                            </Text>
                        </div>
                        <ul className="rai-suggestions-list">
                            {error.suggestions.map((suggestion, index) => (
                                <li key={index}>
                                    <Text size={200}>
                                        {suggestion}
                                    </Text>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                <div className="rai-error-actions">
                    <Text size={300} weight="medium" className="rai-action-text">
                        {error.user_action}
                    </Text>
                    {onRetry && (
                        <Button
                            appearance="primary"
                            onClick={onRetry}
                            className="rai-retry-button"
                        >
                            Try Again
                        </Button>
                    )}
                </div>
            </div>
        </Card>
    );
};

export default RAIErrorCard;
