import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Body1,
    Title2,
    Spinner,
    Button,
    Card,
    CardHeader
} from '@fluentui/react-components';
import { CheckmarkCircle24Regular, DismissCircle24Regular } from '@fluentui/react-icons';
import { apiService } from '../../api/apiService';
import './../../styles/PlanReasoningStream.css';

interface StreamMessage {
    type: 'content' | 'processing' | 'success' | 'error' | 'result';
    content: string;
    timestamp: Date;
}

const PlanReasoningStream: React.FC = () => {
    const { planId } = useParams<{ planId: string }>();
    const navigate = useNavigate();
    const [messages, setMessages] = useState<StreamMessage[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [isComplete, setIsComplete] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        if (!planId) {
            setError('Plan ID is required');
            return;
        }

        startStreaming();
    }, [planId]);

    const addMessage = (type: StreamMessage['type'], content: string) => {
        setMessages(prev => [...prev, {
            type,
            content,
            timestamp: new Date()
        }]);
    };

    const startStreaming = async () => {
        if (!planId) return;

        try {
            setIsStreaming(true);
            setError(null);
            addMessage('processing', 'Starting plan generation...');

            const stream = await apiService.generatePlanStream(planId);
            const reader = stream.getReader();
            const decoder = new TextDecoder();

            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);

                        if (data === '[DONE]') {
                            setIsComplete(true);
                            setIsStreaming(false);
                            return;
                        }

                        if (data.startsWith('ERROR:')) {
                            addMessage('error', data.slice(6));
                            setError(data.slice(6));
                            setIsStreaming(false);
                            return;
                        }

                        if (data.startsWith('[PROCESSING]')) {
                            addMessage('processing', data.slice(12));
                        } else if (data.startsWith('[SUCCESS]')) {
                            addMessage('success', data.slice(9));
                        } else if (data.startsWith('[ERROR]')) {
                            addMessage('error', data.slice(7));
                            setError(data.slice(7));
                        } else if (data.startsWith('[RESULT]')) {
                            try {
                                const result = JSON.parse(data.slice(8));
                                addMessage('result', `Plan generation completed! Created ${result.steps_created} steps.`);
                                setIsComplete(true);
                                setIsStreaming(false);
                            } catch (e) {
                                addMessage('error', 'Failed to parse final result');
                            }
                        } else if (data.trim()) {
                            addMessage('content', data);
                        }
                    }
                }
            }
        } catch (error: any) {
            const errorMessage = error?.message || 'Failed to generate plan';
            setError(errorMessage);
            addMessage('error', errorMessage);
            setIsStreaming(false);
        }
    };

    const handleViewPlan = () => {
        navigate(`/plan/${planId}`);
    };

    const handleGoHome = () => {
        navigate('/');
    };

    const getMessageIcon = (type: StreamMessage['type']) => {
        switch (type) {
            case 'success':
                return <CheckmarkCircle24Regular style={{ color: '#107C10' }} />;
            case 'error':
                return <DismissCircle24Regular style={{ color: '#D13438' }} />;
            case 'processing':
                return <Spinner size="tiny" />;
            default:
                return null;
        }
    };

    const getMessageClass = (type: StreamMessage['type']) => {
        switch (type) {
            case 'processing':
                return 'reasoning-message processing';
            case 'success':
                return 'reasoning-message success';
            case 'error':
                return 'reasoning-message error';
            case 'result':
                return 'reasoning-message result';
            default:
                return 'reasoning-message content';
        }
    };

    return (
        <div className="plan-reasoning-container">
            <div className="plan-reasoning-header">
                <Title2>Creating Your Plan</Title2>
                <Body1>Watch as the AI reasons through your task and creates a detailed plan.</Body1>
            </div>

            <Card className="reasoning-stream-card">
                <CardHeader
                    header={
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {isStreaming && <Spinner size="tiny" />}
                            <span>
                                {isStreaming ? 'Reasoning in progress...' : 
                                 isComplete ? 'Plan generation complete!' : 
                                 error ? 'Generation failed' : 'Preparing to generate plan...'}
                            </span>
                        </div>
                    }
                />

                <div className="reasoning-content">
                    <div className="reasoning-messages">
                        {messages.map((message, index) => (
                            <div key={index} className={getMessageClass(message.type)}>
                                <div className="message-icon">
                                    {getMessageIcon(message.type)}
                                </div>
                                <div className="message-content">
                                    <pre className="message-text">{message.content}</pre>
                                    <div className="message-timestamp">
                                        {message.timestamp.toLocaleTimeString()}
                                    </div>
                                </div>
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                </div>
            </Card>

            <div className="reasoning-actions">
                {isComplete && (
                    <Button 
                        appearance="primary" 
                        onClick={handleViewPlan}
                        style={{ marginRight: '12px' }}
                    >
                        View Plan
                    </Button>
                )}
                <Button 
                    appearance="secondary" 
                    onClick={handleGoHome}
                >
                    Create Another Plan
                </Button>
            </div>
        </div>
    );
};

export default PlanReasoningStream;
