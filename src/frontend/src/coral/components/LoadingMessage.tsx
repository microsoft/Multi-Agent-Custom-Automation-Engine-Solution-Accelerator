import React from 'react';
import {
    Text,
} from "@fluentui/react-components";

export const loadingMessages = [
    "Initializing AI agents...",
    "Generating plan scaffolds...",
    "Optimizing task steps...",
    "Applying finishing touches...",
];

export interface LoadingMessageProps {
    loadingMessage: string;
    iconSrc?: string;
    iconWidth?: number;
    iconHeight?: number;
}

const LoadingMessage: React.FC<LoadingMessageProps> = React.memo(({
    loadingMessage,
    iconSrc,
    iconWidth = 64,
    iconHeight = 64
}) => {
    return (
        <div className="loadingWrapper">
            {iconSrc && (
                <img
                    src={iconSrc}
                    alt="Loading animation"
                    style={{ width: iconWidth, height: iconHeight }}
                />
            )}
            <Text>{loadingMessage}</Text>
        </div>
    );
});
LoadingMessage.displayName = 'LoadingMessage';

export default LoadingMessage;