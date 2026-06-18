import React from "react";
import { AgentMessageData, AgentMessageType } from "@/models";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypePrism from "rehype-prism";
import { Body1, Tag, makeStyles, tokens, Button } from "@fluentui/react-components";
import { TaskService } from "@/store";
import { PersonRegular, ArrowDownloadRegular } from "@fluentui/react-icons";
import { getAgentIcon, getAgentDisplayName } from '@/utils/agentIconUtils';
import { formatJsonInText } from '@/utils/jsonFormatter';

interface StreamingAgentMessageProps {
  agentMessages: AgentMessageData[];
  planData?: any;
  planApprovalRequest?: any;
}

const useStyles = makeStyles({
  container: {
    maxWidth: '800px',
    margin: '0 auto 32px auto',
    padding: '0 24px',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '16px',
    fontFamily: tokens.fontFamilyBase
  },
  avatar: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0
  },
  humanAvatar: {
    backgroundColor: 'var(--colorBrandBackground)'
  },
  botAvatar: {
    backgroundColor: 'var(--colorNeutralBackground3)'
  },
  messageContent: {
    flex: 1,
    maxWidth: 'calc(100% - 48px)',
    display: 'flex',
    flexDirection: 'column'
  },
  humanMessageContent: {
    alignItems: 'flex-end'
  },
  botMessageContent: {
    alignItems: 'flex-start'
  },
  agentHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '8px'
  },
  agentName: {
    fontWeight: '600',
    fontSize: '14px',
    color: 'var(--colorNeutralForeground1)',
    lineHeight: '20px'
  },
  messageBubble: {
    padding: '12px 16px',
    borderRadius: '8px',
    fontSize: '14px',
    lineHeight: '1.5',
    wordWrap: 'break-word'
  },
  humanBubble: {
    backgroundColor: 'var(--colorBrandBackground)',
    color: 'white !important', // Force white text in both light and dark modes
    maxWidth: '80%',
    padding: '12px 16px',
    lineHeight: '1.5',
    alignSelf: 'flex-end'
  },
  botBubble: {
    backgroundColor: 'var(--colorNeutralBackground2)',
    color: 'var(--colorNeutralForeground1)',
    maxWidth: '100%',
    width: '100%',
    boxSizing: 'border-box',
    overflowX: 'hidden',
    alignSelf: 'flex-start',

  },
 
  clarificationBubble: {
    backgroundColor: 'var(--colorNeutralBackground2)',
    color: 'var(--colorNeutralForeground1)',
    padding: '6px 8px', 
    borderRadius: '8px',
    fontSize: '14px',
    lineHeight: '1.5',
    wordWrap: 'break-word',
    maxWidth: '100%',
    alignSelf: 'flex-start'
  },

   actionContainer: {
    display: 'flex',
    alignItems: 'center',
    marginTop: '12px',
    paddingTop: '8px',
    borderTop: '1px solid var(--colorNeutralStroke2)'
  },
  
  copyButton: {
    height: '28px',
    width: '28px'
  },
  sampleTag: {
    fontSize: '11px',
    opacity: 0.7
  }
});

// Check if message is a clarification request
const isClarificationMessage = (content: string): boolean => {
  const clarificationKeywords = [
    'need clarification',
    'please clarify',
    'could you provide more details',
    'i need more information',
    'please specify',
    'what do you mean by',
    'clarification about'
  ];
  
  const lowerContent = content.toLowerCase();
  return clarificationKeywords.some(keyword => lowerContent.includes(keyword));
};

const renderAgentMessages = (
  agentMessages: AgentMessageData[], 
  planData?: any, 
  planApprovalRequest?: any,
  finalResultRef?: React.RefObject<HTMLDivElement>
) => {
  const styles = useStyles();
  
  if (!agentMessages?.length) return null;

  // Filter out messages with empty content
  const validMessages = agentMessages.filter(msg => msg.content?.trim());
  if (!validMessages.length) return null;

  return (
    <>
      {validMessages.map((msg, index) => {
        const isHuman = msg.agent_type === AgentMessageType.HUMAN_AGENT;
        const isClarification = !isHuman && isClarificationMessage(msg.content || '');
        const isLastMessage = index === validMessages.length - 1;

        return (
          <React.Fragment key={index}>
            {/* Scroll anchor placed just before the final message */}
            {isLastMessage && finalResultRef && <div ref={finalResultRef} />}
            <div
              className={styles.container}
              style={{
                flexDirection: isHuman ? 'row-reverse' : 'row'
              }}
            >
            {/* Avatar */}
            <div className={`${styles.avatar} ${isHuman ? styles.humanAvatar : styles.botAvatar}`}>
              {isHuman ? (
                <PersonRegular style={{ fontSize: '16px', color: 'white' }} />
              ) : (
                getAgentIcon(msg.agent, planData, planApprovalRequest)
              )}
            </div>

            {/* Message Content */}
            <div className={`${styles.messageContent} ${isHuman ? styles.humanMessageContent : styles.botMessageContent}`}>
              {/* Agent Header (only for bots) */}
              {!isHuman && (
                <div className={styles.agentHeader}>
                  <Body1 className={styles.agentName}>
                    {getAgentDisplayName(msg.agent)}
                  </Body1>
                  {msg.agent_type !== AgentMessageType.SYSTEM_AGENT && msg.agent?.toLowerCase() !== 'system' && (
                    <Tag
                      appearance="brand"
                    >
                      AI Agent
                    </Tag>
                  )}
                </div>
              )}

              {/* Message Bubble */}
              <div className={
                isHuman 
                  ? `${styles.messageBubble} ${styles.humanBubble}`
                  : isClarification 
                    ? styles.clarificationBubble 
                    : `${styles.messageBubble} ${styles.botBubble}`
              }>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypePrism]}
                  urlTransform={(url: string) => url}
                  components={{
                      a: ({ node: _node, ...props }) => (
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
                      img: ({ node: _imgNode, ...props }) => (
                        <div style={{ position: 'relative', display: 'block', width: '100%', maxWidth: '100%', marginTop: '8px', overflow: 'hidden' }}>
                          <img
                            {...props}
                            style={{ display: 'block', width: '100%', maxWidth: '100%', height: 'auto', borderRadius: '8px' }}
                          />
                          <Button
                            appearance="subtle"
                            icon={<ArrowDownloadRegular />}
                            style={{
                              position: 'absolute',
                              top: '8px',
                              right: '8px',
                              minWidth: '32px',
                              width: '32px',
                              height: '32px',
                              padding: '4px',
                              backgroundColor: 'rgba(0, 0, 0, 0.5)',
                              color: 'white',
                              borderRadius: '4px',
                            }}
                            onClick={async () => {
                              const url = props.src;
                              if (!url) return;
                              const filename = `ad-image-${Date.now()}.png`;
                              try {
                                const response = await fetch(url, { mode: 'cors' });
                                if (!response.ok) throw new Error(`Failed to fetch image (${response.status})`);
                                const blob = await response.blob();
                                const blobUrl = URL.createObjectURL(blob);
                                const link = document.createElement('a');
                                link.href = blobUrl;
                                link.download = filename;
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);
                                URL.revokeObjectURL(blobUrl);
                              } catch (err) {
                                // Fallback: trigger direct download (works for same-origin or CORS-enabled URLs)
                                const link = document.createElement('a');
                                link.href = url;
                                link.download = filename;
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);
                              }
                            }}
                            title="Download image"
                          />
                        </div>
                      ),
                      p: ({ node: _pNode, ...props }) => (
                        <p {...props} style={{ margin: '0 0 8px 0' }} />
                      ),
                      h1: ({ node: _hNode, ...props }) => (
                        <h1 {...props} style={{ fontSize: '20px', fontWeight: 600, margin: '16px 0 8px 0', lineHeight: '1.3' }} />
                      ),
                      h2: ({ node: _hNode, ...props }) => (
                        <h2 {...props} style={{ fontSize: '17px', fontWeight: 600, margin: '14px 0 8px 0', lineHeight: '1.3' }} />
                      ),
                      h3: ({ node: _hNode, ...props }) => (
                        <h3 {...props} style={{ fontSize: '15px', fontWeight: 600, margin: '12px 0 6px 0', lineHeight: '1.3' }} />
                      ),
                      ul: ({ node: _ulNode, ...props }) => (
                        <ul {...props} style={{ margin: '8px 0', paddingLeft: '24px' }} />
                      ),
                      ol: ({ node: _olNode, ...props }) => (
                        <ol {...props} style={{ margin: '8px 0', paddingLeft: '24px' }} />
                      ),
                      li: ({ node: _liNode, ...props }) => (
                        <li {...props} style={{ margin: '4px 0', lineHeight: '1.5' }} />
                      ),
                      blockquote: ({ node: _bqNode, ...props }) => (
                        <blockquote
                          {...props}
                          style={{
                            margin: '8px 0',
                            padding: '8px 12px',
                            borderLeft: '3px solid var(--colorNeutralStroke1)',
                            color: 'var(--colorNeutralForeground2)'
                          }}
                        />
                      )
                    }}
                >
                  {formatJsonInText(TaskService.cleanHRAgent(msg.content) || "")}
                </ReactMarkdown>
              </div>
            </div>
          </div>
          </React.Fragment>
        );
      })}
    </>
  );
};

export default renderAgentMessages;