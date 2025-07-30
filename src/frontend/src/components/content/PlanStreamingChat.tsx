import React, { useEffect, useState, useRef } from 'react';
import {
    Body1,
    Spinner,
    Tag,
    Button,
} from '@fluentui/react-components';
import { 
    CheckmarkCircle24Regular, 
    DismissCircle24Regular,
    DiamondRegular,
    QuestionCircle24Regular
} from '@fluentui/react-icons';
import { Copy } from '../../coral/imports/bundleicons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypePrism from 'rehype-prism';
import { apiService } from '../../api/apiService';
import { TaskService } from '../../services/TaskService';
import '../../styles/PlanChat.css';
import '../../styles/Chat.css';
import '../../styles/prism-material-oceanic.css';

interface StreamMessage {
    type: 'content' | 'processing' | 'success' | 'error' | 'result' | 'reasoning' | 'clarification' | 'completion';
    content: string;
    timestamp: Date;
}

interface PlanStreamingChatProps {
    planId: string;
    onStreamComplete: () => void;
    onStreamError: (error: string) => void;
}

const PlanStreamingChat: React.FC<PlanStreamingChatProps> = ({
    planId,
    onStreamComplete,
    onStreamError
}) => {
    const [messages, setMessages] = useState<StreamMessage[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [isComplete, setIsComplete] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showScrollButton, setShowScrollButton] = useState(false);
    const [isStarting, setIsStarting] = useState(false); // Add this to prevent double-starts
    const [currentThought, setCurrentThought] = useState<string>(''); // For real-time reasoning
    const [isThinking, setIsThinking] = useState(false); // Show thinking indicator
    const [reasoningPhase, setReasoningPhase] = useState<'thinking' | 'planning' | 'complete' | 'clarification'>('thinking');
    
    const messagesContainerRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const streamingRef = useRef(false); // Track if streaming is in progress
    const abortControllerRef = useRef<AbortController | null>(null); // For cancelling requests
    const currentPlanIdRef = useRef<string | null>(null); // Track which plan we're streaming for

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        setShowScrollButton(false);
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Reset state when planId changes to a different plan (not null) - be more conservative
    useEffect(() => {
        if (planId && currentPlanIdRef.current && 
            currentPlanIdRef.current !== planId && 
            !isStreaming && !isThinking) { // Only clear if not currently streaming
            console.log(`Plan ID changed from ${currentPlanIdRef.current} to ${planId}, resetting state`);
            setMessages([]);
            setCurrentThought('');
            setIsStreaming(false);
            setIsComplete(false);
            setError(null);
            setIsStarting(false);
            setIsThinking(false);
            setReasoningPhase('thinking');
            streamingRef.current = false;
            currentPlanIdRef.current = null;
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
                abortControllerRef.current = null;
            }
        }
    }, [planId]);

    useEffect(() => {
        const container = messagesContainerRef.current;
        if (!container) return;

        const handleScroll = () => {
            const { scrollTop, scrollHeight, clientHeight } = container;
            setShowScrollButton(scrollTop + clientHeight < scrollHeight - 100);
        };

        container.addEventListener('scroll', handleScroll);
        return () => container.removeEventListener('scroll', handleScroll);
    }, []);

    useEffect(() => {
        // Only start streaming if we have a planId and haven't already started streaming for this plan
        console.log(`PlanStreamingChat useEffect: planId=${planId}, streamingRef=${streamingRef.current}, isStarting=${isStarting}, isStreaming=${isStreaming}, isComplete=${isComplete}, currentPlanIdRef=${currentPlanIdRef.current}`);
        
        if (planId && 
            !streamingRef.current && 
            !isStarting && 
            !isStreaming && 
            !isComplete &&
            currentPlanIdRef.current !== planId) {
            
            console.log(`PlanStreamingChat: Starting streaming for plan ${planId}`);
            // Set the current plan ID immediately to prevent re-triggers
            currentPlanIdRef.current = planId;
            startStreaming();
        } else {
            console.log(`PlanStreamingChat: Conditions not met to start streaming for plan ${planId}`);
        }
    }, [planId, isComplete]); // Only depend on planId and isComplete

    // Add a ref to track accumulated reasoning content
    const accumulatedReasoningRef = useRef<string>('');
    
    const addMessage = (type: StreamMessage['type'], content: string) => {
        setMessages(prev => [...prev, {
            type,
            content,
            timestamp: new Date()
        }]);
    };

    // New function to accumulate reasoning content
    const addReasoningContent = (content: string) => {
        accumulatedReasoningRef.current += content;
        setCurrentThought(accumulatedReasoningRef.current);
    };

    const lastCallTimeRef = useRef<number>(0);

    const startStreaming = async () => {
        console.log(`startStreaming called for plan ${planId}`);
        if (!planId) {
            console.log('No planId, returning');
            return;
        }
        
        // Prevent duplicate streaming requests - multiple checks for safety
        if (streamingRef.current || isStarting || isStreaming) {
            console.log(`Stream already in progress for plan ${planId}: streamingRef=${streamingRef.current}, isStarting=${isStarting}, isStreaming=${isStreaming}`);
            return;
        }

        // Additional check to prevent rapid successive calls
        const now = Date.now();
        if (now - lastCallTimeRef.current < 1000) { // Prevent calls within 1 second of each other
            console.log(`Preventing rapid successive call for plan ${planId}, last call was ${now - lastCallTimeRef.current}ms ago`);
            return;
        }
        lastCallTimeRef.current = now;

        try {
            // Set all initial states immediately to prevent re-triggers
            setIsStarting(true);
            streamingRef.current = true;
            setIsStreaming(true);
            setIsThinking(true); // Start thinking phase
            setReasoningPhase('thinking');
            setCurrentThought('');
            accumulatedReasoningRef.current = ''; // Reset accumulated reasoning
            setError(null);
            setMessages([]); // Clear previous messages
            setIsComplete(false);
            
            // Cancel any existing request
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
            
            // Create new abort controller
            abortControllerRef.current = new AbortController();
            
            addMessage('processing', 'Starting plan generation...');

            // Add a small delay to ensure the UI is ready
            await new Promise(resolve => setTimeout(resolve, 500));

            const stream = await apiService.generatePlanStream(planId);
            const reader = stream.getReader();
            const decoder = new TextDecoder();

            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    if (buffer.trim()) {
                        // Process any remaining data in buffer
                        const lines = buffer.split('\n');
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const data = line.slice(6);
                                if (data.trim() && data !== '[DONE]') {
                                    addMessage('content', data);
                                }
                            }
                        }
                    }
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
                            setIsStarting(false);
                            setIsThinking(false);
                            setReasoningPhase('complete');
                            streamingRef.current = false;
                            addMessage('success', 'Plan generation completed successfully!');
                            onStreamComplete();
                            return;
                        }

                        if (data.startsWith('ERROR:')) {
                            const errorMsg = data.slice(6);
                            addMessage('error', errorMsg);
                            setError(errorMsg);
                            setIsStreaming(false);
                            setIsStarting(false);
                            setIsThinking(false);
                            streamingRef.current = false;
                            onStreamError(errorMsg);
                            return;
                        }

                        if (data.startsWith('[PROCESSING]')) {
                            setIsThinking(false);
                            setReasoningPhase('planning');
                            addMessage('processing', data.slice(12));
                        } else if (data.startsWith('[REASONING_COMPLETE]')) {
                            setIsThinking(false);
                            setReasoningPhase('planning');
                            // Preserve the reasoning content by adding it as a reasoning message
                            if (accumulatedReasoningRef.current.trim()) {
                                addMessage('reasoning', accumulatedReasoningRef.current);
                            }
                            // Don't add a message for this marker, just transition the UI
                        } else if (data.startsWith('[CLARIFICATION_REQUEST]')) {
                            const clarificationMsg = data.slice(23);
                            addMessage('clarification', clarificationMsg);
                            setReasoningPhase('clarification');
                        } else if (data.startsWith('[COMPLETION_MESSAGE]')) {
                            // Don't show the completion message - just transition to complete
                            setReasoningPhase('complete');
                            setIsThinking(false);
                        } else if (data.startsWith('[PLAN_READY]')) {
                            try {
                                const planData = JSON.parse(data.slice(12));
                                // Complete the streaming and stop all loading indicators
                                setIsComplete(true);
                                setIsStreaming(false);
                                setIsStarting(false);
                                setIsThinking(false);
                                setReasoningPhase('complete');
                                streamingRef.current = false;
                                
                                // Add a simple completion message
                                addMessage('success', `✅ Plan created successfully with ${planData.steps_created || 'multiple'} steps! You can now provide clarifications or ask questions about the plan.`);
                                
                                // Keep the reasoning history visible and notify completion
                                onStreamComplete();
                                return;
                            } catch (e) {
                                addMessage('error', 'Failed to parse plan data');
                            }
                        } else if (data.startsWith('[SUCCESS]')) {
                            addMessage('success', data.slice(9));
                        } else if (data.startsWith('[ERROR]')) {
                            const errorMsg = data.slice(7);
                            addMessage('error', errorMsg);
                            setError(errorMsg);
                        } else if (data.startsWith('[RESULT]')) {
                            try {
                                const result = JSON.parse(data.slice(8));
                                addMessage('completion', `Plan generation completed successfully! Created ${result.steps_created} actionable steps.`);
                                setIsComplete(true);
                                setIsStreaming(false);
                                setIsStarting(false);
                                setIsThinking(false);
                                setReasoningPhase('complete');
                                streamingRef.current = false;
                                // Keep reasoning history visible and call completion
                                onStreamComplete();
                            } catch (e) {
                                addMessage('error', 'Failed to parse final result');
                            }
                        } else if (data.trim()) {
                            // Handle reasoning content - determine phase and accumulate properly
                            if (reasoningPhase === 'thinking') {
                                // During thinking phase, accumulate the reasoning text
                                addReasoningContent(data);
                            } else if (reasoningPhase === 'planning') {
                                // After thinking phase, add as regular planning content
                                addMessage('content', data);
                            } else {
                                // Default case - treat as content
                                addMessage('content', data);
                            }
                        }
                    }
                }
            }
        } catch (error: any) {
            console.error('Streaming error:', error);
            
            // Handle 429 errors (duplicate stream) differently - don't clear the UI
            if (error?.message?.includes('429') || error?.message?.includes('already in progress')) {
                console.log('Duplicate stream detected, maintaining current UI state');
                // Don't add error message or clear state for duplicate streams
                setIsStarting(false);
                streamingRef.current = false;
                return;
            }
            
            const errorMessage = error?.message || 'Failed to generate plan';
            setError(errorMessage);
            addMessage('error', errorMessage);
            setIsStreaming(false);
            onStreamError(errorMessage);
        } finally {
            // Always clean up streaming state
            setIsStarting(false);
            streamingRef.current = false;
            abortControllerRef.current = null;
            // Don't reset the plan ID ref when streaming completes - keep it to prevent clearing messages
            // currentPlanIdRef.current = null;
        }
    };

    // Cleanup function to cancel ongoing requests
    const cleanup = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        streamingRef.current = false;
        setIsStarting(false);
        setIsStreaming(false);
        // Don't reset currentPlanIdRef to preserve message history
        // currentPlanIdRef.current = null;
    };

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            cleanup();
        };
    }, []);

    const getMessageIcon = (type: StreamMessage['type']) => {
        switch (type) {
            case 'success':
                return <CheckmarkCircle24Regular style={{ color: '#107C10' }} />;
            case 'error':
                return <DismissCircle24Regular style={{ color: '#D13438' }} />;
            case 'processing':
                return <Spinner size="tiny" />;
            case 'reasoning':
                return <DiamondRegular style={{ color: '#0078D4' }} />;
            case 'clarification':
                return <QuestionCircle24Regular style={{ color: '#8A2BE2' }} />;
            case 'completion':
                return <CheckmarkCircle24Regular style={{ color: '#28A745' }} />;
            default:
                return null;
        }
    };

    const getMessageClass = (type: StreamMessage['type']) => {
        switch (type) {
            case 'processing':
                return 'message assistant streaming-processing';
            case 'success':
                return 'message assistant streaming-success';
            case 'error':
                return 'message assistant streaming-error';
            case 'result':
                return 'message assistant streaming-result';
            case 'reasoning':
                return 'message assistant streaming-reasoning';
            case 'clarification':
                return 'message assistant streaming-clarification';
            case 'completion':
                return 'message assistant streaming-completion';
            default:
                return 'message assistant';
        }
    };

    const formatContent = (message: StreamMessage) => {
        // For reasoning content, preserve formatting but clean up
        if (message.type === 'content') {
            return TaskService.cleanHRAgent(message.content) || message.content;
        }
        return message.content;
    };

    return (
        <div className="chat-container" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div 
                className="messages" 
                ref={messagesContainerRef}
                style={{ 
                    flex: 1, 
                    overflowY: 'auto', 
                    overflowX: 'hidden',
                    maxHeight: 'calc(100vh - 200px)', // Ensure it doesn't exceed viewport
                    minHeight: '400px' // Minimum height for usability
                }}
            >
                <div className="message-wrapper">
                    {/* Header message */}
                    <div className="message assistant">
                        <div className="plan-chat-header">
                            <div className="plan-chat-speaker">
                                <Body1 className="speaker-name">AI Reasoning Engine</Body1>
                                <Tag size="extra-small" shape="rounded" appearance="brand" className="bot-tag">
                                    {isThinking ? 'THINKING' : 
                                     reasoningPhase === 'planning' ? 'PLANNING' : 
                                     isComplete || reasoningPhase === 'complete' ? 'COMPLETE' : 'BOT'}
                                </Tag>
                            </div>
                        </div>
                        <Body1>
                            <div className="plan-chat-message-content">
                                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypePrism]}>
                                    {isThinking 
                                        ? "🤔 I'm thinking through your request and analyzing the best approach..."
                                        : reasoningPhase === 'planning'
                                        ? "📋 Creating your detailed plan with actionable steps..."
                                        : isComplete 
                                        ? "✅ Plan generation complete! I've created a detailed plan with steps for your task."
                                        : "Preparing to generate your plan..."
                                    }
                                </ReactMarkdown>
                                <div className="assistant-footer">
                                    <div className="assistant-actions">
                                        <Tag
                                            icon={<DiamondRegular />}
                                            appearance="filled"
                                            size="extra-small"
                                        >
                                            AI reasoning process in real-time
                                        </Tag>
                                    </div>
                                </div>
                            </div>
                        </Body1>
                    </div>

                    {/* Thinking display - similar to ChatGPT reasoning - show during thinking and after completion if we have content */}
                    {(isThinking || (currentThought && currentThought.trim())) && (
                        <div className="message assistant thinking-message">
                            <div className="plan-chat-header">
                                <div className="plan-chat-speaker">
                                    <Body1 className="speaker-name">
                                        {isThinking ? '🧠 Thinking...' : '💭 Reasoning Complete'}
                                    </Body1>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                        {isThinking && <Spinner size="tiny" />}
                                        <Tag size="extra-small" shape="rounded" appearance="outline" className="thinking-tag">
                                            {isThinking ? 'REASONING' : 'THOUGHT'}
                                        </Tag>
                                    </div>
                                </div>
                            </div>
                            <Body1>
                                <div className="plan-chat-message-content thinking-content">
                                    <details open={true}>
                                        <summary style={{ cursor: 'pointer', marginBottom: '8px', fontWeight: 'bold' }}>
                                            {isThinking ? 'View reasoning process...' : 'AI Reasoning Process'}
                                        </summary>
                                        <div style={{ 
                                            background: '#f8f9fa', 
                                            padding: '12px', 
                                            borderRadius: '8px', 
                                            fontSize: '14px',
                                            fontFamily: 'monospace',
                                            whiteSpace: 'pre-wrap',
                                            border: '1px solid #e1e4e8',
                                            maxHeight: '500px',
                                            overflowY: 'auto',
                                            overflowX: 'hidden',
                                            wordWrap: 'break-word'
                                        }}>
                                            {currentThought || 'Analyzing your request...'}
                                            {isThinking && <span className="thinking-cursor">|</span>}
                                        </div>
                                    </details>
                                </div>
                            </Body1>
                        </div>
                    )}

                    {/* Streaming messages */}
                    {messages.map((message, index) => (
                        <div key={index} className={getMessageClass(message.type)}>
                            <div className="plan-chat-header">
                                <div className="plan-chat-speaker">
                                    <Body1 className="speaker-name">
                                        {message.type === 'processing' ? 'Planning...' : 
                                         message.type === 'success' ? 'Success' :
                                         message.type === 'error' ? 'Error' :
                                         message.type === 'result' ? 'Result' : 
                                         message.type === 'reasoning' ? 'AI Reasoning' : 
                                         message.type === 'clarification' ? 'Clarification Request' : 
                                         message.type === 'completion' ? 'Plan Generated' : 'Content'}
                                    </Body1>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                        {getMessageIcon(message.type)}
                                        <Tag size="extra-small" shape="rounded" appearance="brand" className="bot-tag">
                                            AI
                                        </Tag>
                                    </div>
                                </div>
                            </div>
                            <Body1>
                                <div className="plan-chat-message-content">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypePrism]}>
                                        {formatContent(message)}
                                    </ReactMarkdown>
                                    <div className="assistant-footer">
                                        <div className="assistant-actions">
                                            <div>
                                                <Button
                                                    onClick={() => navigator.clipboard.writeText(message.content)}
                                                    title="Copy Response"
                                                    appearance="subtle"
                                                    style={{ height: 28, width: 28 }}
                                                    icon={<Copy />}
                                                />
                                            </div>
                                            <div className="message-timestamp">
                                                {message.timestamp.toLocaleTimeString()}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </Body1>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {showScrollButton && (
                <Tag
                    onClick={scrollToBottom}
                    className="scroll-to-bottom plan-chat-scroll-button"
                    shape="circular"
                    style={{
                        bottom: 16,
                        position: 'absolute',
                        right: 16,
                        zIndex: 5,
                    }}
                >
                    Back to bottom
                </Tag>
            )}
        </div>
    );
};

export default PlanStreamingChat;
