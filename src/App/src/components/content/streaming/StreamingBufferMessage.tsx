import React, { useState, useEffect, useRef } from 'react';
import {
    Button,
} from '@fluentui/react-components';
import { CheckmarkCircle20Regular, ArrowTurnDownRightRegular } from '@fluentui/react-icons';
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypePrism from "rehype-prism";

interface StreamingBufferMessageProps {
    streamingMessageBuffer: string;
    isStreaming?: boolean;
}

/**
 * Format a key from snake_case / camelCase / kebab-case into a readable label.
 */
const humanizeKey = (key: string): string => {
    if (!key) return key;
    const spaced = key
        .replace(/[_-]+/g, ' ')
        .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
        .trim();
    return spaced.replace(/\b\w/g, (c) => c.toUpperCase());
};

/**
 * Render a parsed JSON value as readable Markdown (bullet list of
 * "**Key**: value" entries, recursing into nested objects/arrays).
 */
const jsonToMarkdown = (value: any, depth = 0): string => {
    const indent = '  '.repeat(depth);

    if (value === null || value === undefined) return `${indent}_n/a_`;

    if (Array.isArray(value)) {
        if (value.length === 0) return `${indent}_(none)_`;
        return value
            .map((item) => {
                if (item !== null && typeof item === 'object') {
                    return `${indent}- \n${jsonToMarkdown(item, depth + 1)}`;
                }
                return `${indent}- ${String(item)}`;
            })
            .join('\n');
    }

    if (typeof value === 'object') {
        const entries = Object.entries(value);
        if (entries.length === 0) return `${indent}_(empty)_`;
        return entries
            .map(([k, v]) => {
                const label = humanizeKey(k);
                if (v !== null && typeof v === 'object') {
                    return `${indent}- **${label}:**\n${jsonToMarkdown(v, depth + 1)}`;
                }
                return `${indent}- **${label}:** ${v === null || v === undefined ? '' : String(v)}`;
            })
            .join('\n');
    }

    return `${indent}${String(value)}`;
};

/**
 * Detect raw JSON blocks in the streaming buffer and replace them with a
 * readable Markdown rendering so the Details section doesn't expose raw JSON.
 * Lines that already sit inside an existing fenced code block are left alone.
 */
const formatBufferContent = (content: string): string => {
    if (!content) return content;

    const lines = content.split('\n');
    const out: string[] = [];
    let insideExistingFence = false;
    let i = 0;

    while (i < lines.length) {
        const line = lines[i];
        const trimmed = line.trim();

        if (trimmed.startsWith('```')) {
            insideExistingFence = !insideExistingFence;
            out.push(line);
            i++;
            continue;
        }

        if (!insideExistingFence && (trimmed.startsWith('{') || trimmed.startsWith('['))) {
            // Try to capture a balanced JSON block starting at this line
            let depth = 0;
            let endIdx = -1;
            for (let j = i; j < lines.length; j++) {
                const l = lines[j];
                for (const ch of l) {
                    if (ch === '{' || ch === '[') depth++;
                    else if (ch === '}' || ch === ']') depth--;
                }
                if (depth === 0) {
                    endIdx = j;
                    break;
                }
            }
            if (endIdx !== -1) {
                const block = lines.slice(i, endIdx + 1).join('\n');
                try {
                    const parsed = JSON.parse(block);
                    out.push(jsonToMarkdown(parsed));
                    out.push('');
                    i = endIdx + 1;
                    continue;
                } catch {
                    // Not valid JSON — fall through and keep the original line
                }
            }
        }

        out.push(line);
        i++;
    }

    return out.join('\n');
};

// Convert to a proper React component instead of a function
const StreamingBufferMessage: React.FC<StreamingBufferMessageProps> = ({
    streamingMessageBuffer,
    isStreaming = false
}) => {
    const [isExpanded, setIsExpanded] = useState<boolean>(false);
    const [shouldFade, setShouldFade] = useState<boolean>(false);
    const contentRef = useRef<HTMLDivElement>(null);
    const prevBufferLength = useRef<number>(0);

    // Trigger fade effect when new content is being streamed
    useEffect(() => {
        if (isStreaming && streamingMessageBuffer.length > prevBufferLength.current) {
            setShouldFade(true);
            const timer = setTimeout(() => setShouldFade(false), 300);
            prevBufferLength.current = streamingMessageBuffer.length;
            return () => clearTimeout(timer);
        }
        prevBufferLength.current = streamingMessageBuffer.length;
    }, [streamingMessageBuffer, isStreaming]);

    // Auto-scroll to bottom when streaming
    useEffect(() => {
        if (isStreaming && !isExpanded && contentRef.current) {
            contentRef.current.scrollTop = contentRef.current.scrollHeight;
        }
    }, [streamingMessageBuffer, isStreaming, isExpanded]);

    if (!streamingMessageBuffer || streamingMessageBuffer.trim() === "") return null;

    const formattedBuffer = formatBufferContent(streamingMessageBuffer);

    return (
        <div style={{
            maxWidth: '800px',
            margin: '0 auto 32px auto',
            padding: '0 24px'
        }}>
            <div style={{
                backgroundColor: 'var(--colorNeutralBackground2)',
                border: '1px solid var(--colorNeutralStroke2)',
                borderRadius: '8px',
                padding: '16px',
                fontSize: '14px',
                lineHeight: '1.5',
                height: isExpanded ? 'auto' : '256px',
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
                overflow: isExpanded ? 'visible' : 'hidden'
            }}>
                {/* Header */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: isExpanded ? '16px' : '16px',
                    flexShrink: 0
                }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px'
                    }}>
                        <CheckmarkCircle20Regular style={{
                            fontSize: '20px',
                            color: 'var(--colorNeutralForeground1)',
                            width: '20px',
                            height: '20px',
                            flexShrink: 0
                        }} />
                        <span style={{
                            fontWeight: '500',
                            color: 'var(--colorNeutralForeground1)',
                            fontSize: '14px',
                            lineHeight: '20px'
                        }}>
                            AI Thinking Process
                        </span>
                    </div>

                    <Button
                        appearance="secondary"
                        size="small"
                        onClick={() => setIsExpanded(!isExpanded)}
                        style={{
                            backgroundColor: 'var(--colorNeutralBackground3)',
                            border: '1px solid var(--colorNeutralStroke2)',
                            borderRadius: '16px',
                            padding: '4px 12px',
                            fontSize: '14px'
                        }}
                    >
                        {isExpanded ? 'Hide' : 'Details'}
                    </Button>
                </div>

                {/* Content area - collapsed state */}
                {!isExpanded && (
                    <div
                        ref={contentRef}
                        style={{
                            flex: 1,
                            position: 'relative',
                            overflowY: 'hidden',
                            overflowX: 'hidden',
                            paddingLeft: '32px',
                            transition: 'opacity 0.3s ease-in-out',
                            opacity: shouldFade ? 0.6 : 1
                        }}
                    >
                        {/* Top fade overlay for collapsed state */}
                        <div style={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            height: '40px',
                            background: 'linear-gradient(to bottom, var(--colorNeutralBackground2), transparent)',
                            pointerEvents: 'none',
                            zIndex: 1
                        }} />

                        <div style={{
                            display: 'flex',
                            alignItems: 'flex-end',
                            gap: '8px',
                            height: '100%'
                        }}>
                            <ArrowTurnDownRightRegular style={{
                                color: 'var(--colorNeutralForeground3)',
                                fontSize: '14px',
                                marginBottom: '2px',
                                flexShrink: 0
                            }} />
                            <div style={{
                                color: 'var(--colorNeutralForeground2)',
                                fontSize: '14px',
                                lineHeight: '1.4',
                                height: '100%',
                                overflow: 'hidden',
                                wordWrap: 'break-word',
                                display: 'flex',
                                flexDirection: 'column',
                                justifyContent: 'flex-end',
                                maskImage: 'linear-gradient(to bottom, transparent 0%, black 30%, black 100%)',
                                WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 30%, black 100%)'
                            }}>
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    rehypePlugins={[rehypePrism]}
                                    components={{
                                        a: ({ node, ...props }) => (
                                            <a
                                                {...props}
                                                style={{
                                                    color: 'var(--colorNeutralBrandForeground1)',
                                                    textDecoration: 'none'
                                                }}
                                                onMouseEnter={(e) => {
                                                    e.currentTarget.style.textDecoration = 'underline';
                                                }}
                                                onMouseLeave={(e) => {
                                                    e.currentTarget.style.textDecoration = 'none';
                                                }}
                                            />
                                        ),
                                        p: ({ node, ...props }) => (
                                            <p {...props} style={{ margin: '0 0 8px 0' }} />
                                        )
                                    }}
                                >
                                    {formattedBuffer}
                                </ReactMarkdown>
                            </div>
                        </div>
                    </div>
                )}

                {/* Content area - expanded state */}
                {isExpanded && (
                    <div style={{
                        padding: '12px',
                        marginTop: '8px'
                    }}>
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypePrism]}
                            components={{
                                a: ({ node, ...props }) => (
                                    <a
                                        {...props}
                                        style={{
                                            color: 'var(--colorNeutralBrandForeground1)',
                                            textDecoration: 'none'
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.textDecoration = 'underline';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.textDecoration = 'none';
                                        }}
                                    />
                                )
                            }}
                        >
                            {formattedBuffer}
                        </ReactMarkdown>
                    </div>
                )}
            </div>
        </div>
    );
};

const MemoizedStreamingBufferMessage = React.memo(StreamingBufferMessage);
MemoizedStreamingBufferMessage.displayName = 'StreamingBufferMessage';
export default MemoizedStreamingBufferMessage;