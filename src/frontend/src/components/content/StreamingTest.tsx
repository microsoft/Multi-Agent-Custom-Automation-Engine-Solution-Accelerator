import React, { useState } from 'react';
import { Button, Body1 } from '@fluentui/react-components';

const StreamingTest: React.FC = () => {
    const [messages, setMessages] = useState<string[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);

    const testStreaming = async () => {
        setIsStreaming(true);
        setMessages([]);

        try {
            const response = await fetch('http://localhost:8000/api/generate_plan/test-plan-id', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer test-token',
                },
            });

            if (!response.body) {
                throw new Error('No response body');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            setIsStreaming(false);
                            return;
                        }
                        if (data.trim()) {
                            setMessages(prev => [...prev, data]);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Streaming error:', error);
            setMessages(prev => [...prev, `Error: ${error}`]);
        } finally {
            setIsStreaming(false);
        }
    };

    return (
        <div style={{ padding: '20px' }}>
            <Body1>Streaming Test</Body1>
            <Button onClick={testStreaming} disabled={isStreaming}>
                {isStreaming ? 'Streaming...' : 'Test Stream'}
            </Button>
            <div style={{ marginTop: '20px', maxHeight: '400px', overflow: 'auto' }}>
                {messages.map((msg, index) => (
                    <div key={index} style={{ marginBottom: '8px', padding: '8px', backgroundColor: '#f5f5f5' }}>
                        {msg}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default StreamingTest;
