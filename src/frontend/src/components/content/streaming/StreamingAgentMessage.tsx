import React, { useMemo } from "react";
import { AgentMessageData, AgentMessageType } from "@/models";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypePrism from "rehype-prism";
import { Body1, Tag, makeStyles, tokens } from "@fluentui/react-components";
import { cleanHRAgentText } from "@/utils/messageUtils";
import { PersonRegular } from "@fluentui/react-icons";
import { getAgentIcon, getAgentDisplayName } from "@/utils/agentIconUtils";

// ─── Shared styles ───────────────────────────────────────────────────────────

const useStyles = makeStyles({
    container: {
        maxWidth: "800px",
        margin: "0 auto 32px auto",
        padding: "0 24px",
        display: "flex",
        alignItems: "flex-start",
        gap: "16px",
        fontFamily: tokens.fontFamilyBase,
    },
    avatar: {
        width: "32px",
        height: "32px",
        borderRadius: "50%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
    },
    humanAvatar: {
        backgroundColor: "var(--colorBrandBackground)",
    },
    botAvatar: {
        backgroundColor: "var(--colorNeutralBackground3)",
    },
    messageContent: {
        flex: 1,
        maxWidth: "calc(100% - 48px)",
        display: "flex",
        flexDirection: "column",
    },
    humanMessageContent: {
        alignItems: "flex-end",
    },
    botMessageContent: {
        alignItems: "flex-start",
    },
    agentHeader: {
        display: "flex",
        alignItems: "center",
        gap: "12px",
        marginBottom: "8px",
    },
    agentName: {
        fontWeight: "600",
        fontSize: "14px",
        color: "var(--colorNeutralForeground1)",
        lineHeight: "20px",
    },
    messageBubble: {
        padding: "12px 16px",
        borderRadius: "8px",
        fontSize: "14px",
        lineHeight: "1.5",
        wordWrap: "break-word",
    },
    humanBubble: {
        backgroundColor: "var(--colorBrandBackground)",
        color: "white !important",
        maxWidth: "80%",
        padding: "12px 16px",
        lineHeight: "1.5",
        alignSelf: "flex-end",
    },
    botBubble: {
        backgroundColor: "var(--colorNeutralBackground2)",
        color: "var(--colorNeutralForeground1)",
        maxWidth: "100%",
        alignSelf: "flex-start",
    },
    clarificationBubble: {
        backgroundColor: "var(--colorNeutralBackground2)",
        color: "var(--colorNeutralForeground1)",
        padding: "6px 8px",
        borderRadius: "8px",
        fontSize: "14px",
        lineHeight: "1.5",
        wordWrap: "break-word",
        maxWidth: "100%",
        alignSelf: "flex-start",
    },
    actionContainer: {
        display: "flex",
        alignItems: "center",
        marginTop: "12px",
        paddingTop: "8px",
        borderTop: "1px solid var(--colorNeutralStroke2)",
    },
    copyButton: {
        height: "28px",
        width: "28px",
    },
    sampleTag: {
        fontSize: "11px",
        opacity: 0.7,
    },
});

// ─── Shared markdown link renderer ──────────────────────────────────────────

const markdownLinkRenderer = ({ node, ...props }: any) => (
    <a
        {...props}
        style={{ color: "var(--colorNeutralBrandForeground1)", textDecoration: "none" }}
        onMouseEnter={(e) => { e.currentTarget.style.textDecoration = "underline"; }}
        onMouseLeave={(e) => { e.currentTarget.style.textDecoration = "none"; }}
    />
);

// ─── Utility ─────────────────────────────────────────────────────────────────

/** Check if message content is a clarification request */
const isClarificationMessage = (content: string): boolean => {
    const keywords = [
        "need clarification",
        "please clarify",
        "could you provide more details",
        "i need more information",
        "please specify",
        "what do you mean by",
        "clarification about",
    ];
    const lower = content.toLowerCase();
    return keywords.some((kw) => lower.includes(kw));
};

// ─── Individual message-type components ─────────────────────────────────────

/** Props shared by all single-message components */
export interface SingleMessageProps {
    message: AgentMessageData;
    planData?: any;
    planApprovalRequest?: any;
}

/**
 * Renders a human (user) message – right-aligned with branded bubble.
 * Handles a single message type: human/user chat message.
 */
export const HumanMessageItem: React.FC<SingleMessageProps> = React.memo(({ message }) => {
    const styles = useStyles();

    return (
        <div className={styles.container} style={{ flexDirection: "row-reverse" }}>
            <div className={`${styles.avatar} ${styles.humanAvatar}`}>
                <PersonRegular style={{ fontSize: "16px", color: "white" }} />
            </div>
            <div className={`${styles.messageContent} ${styles.humanMessageContent}`}>
                <div className={`${styles.messageBubble} ${styles.humanBubble}`}>
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypePrism]}
                        components={{ a: markdownLinkRenderer }}
                    >
                        {cleanHRAgentText(message.content) || ""}
                    </ReactMarkdown>
                </div>
            </div>
        </div>
    );
});
HumanMessageItem.displayName = 'HumanMessageItem';

/**
 * Renders an AI bot message – left-aligned with agent header and neutral bubble.
 * Handles a single message type: AI agent response message.
 */
export const BotMessageItem: React.FC<SingleMessageProps> = React.memo(({
    message,
    planData,
    planApprovalRequest,
}) => {
    const styles = useStyles();
    const isClarification = isClarificationMessage(message.content || "");

    return (
        <div className={styles.container} style={{ flexDirection: "row" }}>
            <div className={`${styles.avatar} ${styles.botAvatar}`}>
                {getAgentIcon(message.agent, planData, planApprovalRequest)}
            </div>
            <div className={`${styles.messageContent} ${styles.botMessageContent}`}>
                <div className={styles.agentHeader}>
                    <Body1 className={styles.agentName}>
                        {getAgentDisplayName(message.agent)}
                    </Body1>
                    <Tag appearance="brand">AI Agent</Tag>
                </div>
                <div
                    className={
                        isClarification
                            ? styles.clarificationBubble
                            : `${styles.messageBubble} ${styles.botBubble}`
                    }
                >
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypePrism]}
                        components={{ a: markdownLinkRenderer }}
                    >
                        {cleanHRAgentText(message.content) || ""}
                    </ReactMarkdown>
                </div>
            </div>
        </div>
    );
});
BotMessageItem.displayName = 'BotMessageItem';

/**
 * Renders a system error message – left-aligned with error styling.
 * Handles a single message type: system/error messages.
 */
export const ErrorMessageItem: React.FC<SingleMessageProps> = React.memo(({
    message,
    planData,
    planApprovalRequest,
}) => {
    const styles = useStyles();

    return (
        <div className={styles.container} style={{ flexDirection: "row" }}>
            <div className={`${styles.avatar} ${styles.botAvatar}`}>
                {getAgentIcon(message.agent, planData, planApprovalRequest)}
            </div>
            <div className={`${styles.messageContent} ${styles.botMessageContent}`}>
                <div className={styles.agentHeader}>
                    <Body1 className={styles.agentName}>
                        {getAgentDisplayName(message.agent)}
                    </Body1>
                </div>
                <div className={`${styles.messageBubble} ${styles.botBubble}`}>
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypePrism]}
                        components={{ a: markdownLinkRenderer }}
                    >
                        {cleanHRAgentText(message.content) || ""}
                    </ReactMarkdown>
                </div>
            </div>
        </div>
    );
});
ErrorMessageItem.displayName = 'ErrorMessageItem';

// ─── AgentMessageList (orchestrator) ─────────────────────────────────────────

/** Props for the AgentMessageList component */
export interface AgentMessageListProps {
    agentMessages: AgentMessageData[];
    planData?: any;
    planApprovalRequest?: any;
}

/**
 * Iterates over all agent messages and delegates to the correct single-message
 * component based on agent_type (human, system/error, or bot).
 */
const AgentMessageList: React.FC<AgentMessageListProps> = React.memo(({
    agentMessages,
    planData,
    planApprovalRequest,
}) => {
    const validMessages = useMemo(
        () => agentMessages.filter((msg) => msg.content?.trim()),
        [agentMessages]
    );

    if (!agentMessages?.length) return null;
    if (!validMessages.length) return null;

    return (
        <>
            {validMessages.map((msg, index) => {
                const commonProps: SingleMessageProps = {
                    message: msg,
                    planData,
                    planApprovalRequest,
                };

                // Human / user message
                if (msg.agent_type === AgentMessageType.HUMAN_AGENT) {
                    return <HumanMessageItem key={index} {...commonProps} />;
                }

                // System / error message
                if (msg.agent_type === AgentMessageType.SYSTEM_AGENT) {
                    return <ErrorMessageItem key={index} {...commonProps} />;
                }

                // AI agent / bot message (default)
                return <BotMessageItem key={index} {...commonProps} />;
            })}
        </>
    );
});
AgentMessageList.displayName = 'AgentMessageList';

// ─── Backward-compatible render function (deprecated) ────────────────────────

/** @deprecated Use `<AgentMessageList>` component instead */
const renderAgentMessages = (
    agentMessages: AgentMessageData[],
    planData?: any,
    planApprovalRequest?: any
) => (
    <AgentMessageList
        agentMessages={agentMessages}
        planData={planData}
        planApprovalRequest={planApprovalRequest}
    />
);

export { AgentMessageList };
export default renderAgentMessages;
