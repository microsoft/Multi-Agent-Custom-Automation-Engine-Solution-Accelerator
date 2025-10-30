import React, { useState } from 'react';
import { Card, Title3, Body1, Button, Textarea } from '@fluentui/react-components';
import { Send20Regular } from '@fluentui/react-icons';
import { ParsedUserClarification } from '../../models';
import '../../styles/SimplePlanChat.css';

interface SimplePlanChatProps {
    clarificationRequest: ParsedUserClarification | null;
    onSubmitClarification: (answer: string) => void;
    disabled: boolean;
}

const SimplePlanChat: React.FC<SimplePlanChatProps> = ({
    clarificationRequest,
    onSubmitClarification,
    disabled
}) => {
    const [answer, setAnswer] = useState('');

    const handleSubmit = () => {
        if (answer.trim()) {
            onSubmitClarification(answer.trim());
            setAnswer('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    if (!clarificationRequest) return null;

    return (
        <Card className="simple-plan-chat">
            <div className="simple-plan-chat__header">
                <Title3>I need more information:</Title3>
            </div>
            
            <div className="simple-plan-chat__question">
                <Body1>{clarificationRequest.question}</Body1>
            </div>

            <div className="simple-plan-chat__input-section">
                <Textarea
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type your response here..."
                    disabled={disabled}
                    resize="vertical"
                    className="simple-plan-chat__textarea"
                />
                <Button
                    appearance="primary"
                    icon={<Send20Regular />}
                    onClick={handleSubmit}
                    disabled={disabled || !answer.trim()}
                >
                    Send
                </Button>
            </div>
        </Card>
    );
};

export default SimplePlanChat;











