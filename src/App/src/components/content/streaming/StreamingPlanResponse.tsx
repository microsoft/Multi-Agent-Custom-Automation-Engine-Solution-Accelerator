import { MPlanData } from "@/models";
import { 
    Button, 
    Text,  
    Body1, 
    Tag,
    makeStyles,
    tokens
} from "@fluentui/react-components";
import { 
    CheckmarkCircle20Regular 
} from "@fluentui/react-icons";
import React, { useState } from 'react';
import { getAgentIcon, getAgentDisplayName } from '@/utils/agentIconUtils';

// Updated styles to match consistent spacing and remove brand colors from bot elements
const useStyles = makeStyles({
    container: {
        maxWidth: '800px',
        margin: '0 auto 32px auto',
        padding: '0 24px',
        fontFamily: tokens.fontFamilyBase
    },
    agentHeader: {
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        marginBottom: '8px'
    },
    agentAvatar: {
        width: '32px',
        height: '32px',
        borderRadius: '50%',
        backgroundColor: 'var(--colorNeutralBackground3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
    },
    hiddenAvatar: {
        width: '32px',
        height: '32px',
        visibility: 'hidden',
        flexShrink: 0
    },
    agentInfo: {
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        flex: 1
    },
    agentName: {
        fontSize: '14px',
        fontWeight: '600',
        color: 'var(--colorNeutralForeground1)',
        lineHeight: '20px'
    },
    messageContainer: {
        backgroundColor: 'var(--colorNeutralBackground2)',
        padding: '12px 16px',
        borderRadius: '8px',
        fontSize: '14px',
        lineHeight: '1.5',
        wordWrap: 'break-word'
    },
    factsSection: {
        backgroundColor: 'var(--colorNeutralBackground2)',
        border: '1px solid var(--colorNeutralStroke2)',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '16px'
    },
    factsHeader: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px'
    },
    factsHeaderLeft: {
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
    },
    factsTitle: {
        fontWeight: '500',
        color: 'var(--colorNeutralForeground1)',
        fontSize: '14px',
        lineHeight: '20px'
    },
    factsButton: {
        backgroundColor: 'var(--colorNeutralBackground3)',
        border: '1px solid var(--colorNeutralStroke2)',
        borderRadius: '16px',
        padding: '4px 12px',
        fontSize: '14px',
        fontWeight: '500',
        cursor: 'pointer'
    },
    factsPreview: {
        fontSize: '14px',
        lineHeight: '1.4',
        color: 'var(--colorNeutralForeground2)',
        marginTop: '8px'
    },
    factsContent: {
        fontSize: '14px',
        lineHeight: '1.5',
        color: 'var(--colorNeutralForeground2)',
        marginTop: '8px',
        whiteSpace: 'pre-wrap'
    },
    planTitle: {
        marginBottom: '20px',
        fontSize: '18px',
        fontWeight: '600',
        color: 'var(--colorNeutralForeground1)',
        lineHeight: '24px'
    },
    stepsList: {
        marginBottom: '16px'
    },
    stepItem: {
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        marginBottom: '12px'
    },
    stepNumber: {
        minWidth: '24px',
        height: '24px',
        borderRadius: '50%',
        backgroundColor: 'var(--colorNeutralBackground3)',
        border: '1px solid var(--colorNeutralStroke2)',
        color: 'var(--colorNeutralForeground1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '12px',
        fontWeight: '600',
        flexShrink: 0,
        marginTop: '2px'
    },
    stepText: {
        fontSize: '14px',
        color: 'var(--colorNeutralForeground1)',
        lineHeight: '1.5',
        flex: 1,
        wordWrap: 'break-word',
        overflowWrap: 'break-word'
    },
    stepHeading: {
        marginBottom: '12px',
        fontSize: '16px',
        fontWeight: '600',
        color: 'var(--colorNeutralForeground1)',
        lineHeight: '22px'
    },
    instructionText: {
        color: 'var(--colorNeutralForeground2)',
        fontSize: '14px',
        lineHeight: '1.5',
        marginBottom: '16px'
    },
    buttonContainer: {
        display: 'flex',
        gap: '12px',
        alignItems: 'center',
        marginTop: '20px'
    }
});

// Function to get agent name from backend data using the centralized utility
const getAgentDisplayNameFromPlan = (planApprovalRequest: MPlanData | null): string => {
    if (planApprovalRequest?.steps?.length) {
        const firstAgent = planApprovalRequest.steps.find(step => step.agent)?.agent;
        if (firstAgent) {
            return getAgentDisplayName(firstAgent);
        }
    }
    return getAgentDisplayName('Planning Agent');
};

// Dynamically extract content from whatever fields contain data
const extractDynamicContent = (planApprovalRequest: MPlanData): { 
    factsContent: string; 
    planSteps: Array<{ type: 'heading' | 'substep'; text: string }> 
} => {
    if (!planApprovalRequest) return { factsContent: '', planSteps: [] };

    let factsContent = '';
    let planSteps: Array<{ type: 'heading' | 'substep'; text: string }> = [];

    // Build facts content from available sources
    const factsSources: string[] = [];

    // Add team assembly if available
    if (planApprovalRequest.context?.participant_descriptions && 
        Object.keys(planApprovalRequest.context.participant_descriptions).length > 0) {
        let teamContent = 'Team Assembly:\n\n';
        Object.entries(planApprovalRequest.context.participant_descriptions).forEach(([agent, description]) => {
            teamContent += `${agent}: ${description}\n\n`;
        });
        factsSources.push(teamContent);
    }

    // Add facts field if it contains substantial content
    if (planApprovalRequest.facts && planApprovalRequest.facts.trim().length > 10) {
        factsSources.push(planApprovalRequest.facts.trim());
    }

    // Combine all facts sources
    factsContent = factsSources.join('\n---\n\n');

    // Extract plan steps from multiple possible sources
    if (planApprovalRequest.steps && planApprovalRequest.steps.length > 0) {
        planApprovalRequest.steps.forEach(step => {
            // Use whichever action field has content
            const action = step.action || step.cleanAction || '';
            if (action.trim()) {
                // Check if it ends with colon (heading) or is a regular step
                if (action.trim().endsWith(':')) {
                    planSteps.push({ type: 'heading', text: action.trim() });
                } else {
                    planSteps.push({ type: 'substep', text: action.trim() });
                }
            }
        });
    }

    // If no steps found in steps array, try to extract from other fields
    if (planSteps.length === 0) {
        // Look in user_request or facts for plan content
        const searchContent = planApprovalRequest.user_request || planApprovalRequest.facts || '';
        const lines = searchContent.split('\n');
        
        for (const line of lines) {
            const trimmedLine = line.trim();
            
            // Skip empty lines and section headers
            if (!trimmedLine || 
                trimmedLine.toLowerCase().includes('plan created') ||
                trimmedLine.toLowerCase().includes('user request') ||
                trimmedLine.toLowerCase().includes('team assembly') ||
                trimmedLine.toLowerCase().includes('fact sheet')) {
                continue;
            }
            
            // Look for bullet points, dashes, or numbered items
            if (trimmedLine.match(/^[-•*]\s+/) || 
                trimmedLine.match(/^\d+\.\s+/) ||
                trimmedLine.match(/^[a-zA-Z][\w\s]*:$/)) {
                
                // Remove bullet/number prefixes for clean display
                let cleanText = trimmedLine
                    .replace(/^[-•*]\s+/, '')
                    .replace(/^\d+\.\s+/, '')
                    .trim();
                
                if (cleanText.length > 3) {
                    // Determine if it's a heading (ends with colon) or substep
                    if (cleanText.endsWith(':')) {
                        planSteps.push({ type: 'heading', text: cleanText });
                    } else {
                        planSteps.push({ type: 'substep', text: cleanText });
                    }
                }
            }
        }
    }

    return { factsContent, planSteps };
};

// Process facts for preview
const getFactsPreview = (content: string): string => {
    if (!content) return '';
    return content.length > 200 ? content.substring(0, 200) + "..." : content;
};

// FluentUI-based plan response component with consistent spacing and proper colors
const renderPlanResponse = (
    planApprovalRequest: MPlanData | null, 
    handleApprovePlan: () => void, 
    handleRejectPlan: () => void, 
    processingApproval: boolean, 
    showApprovalButtons: boolean
) => {
    const styles = useStyles();
    const [isFactsExpanded, setIsFactsExpanded] = useState(false);
    
    if (!planApprovalRequest) return null;

    const agentName = getAgentDisplayNameFromPlan(planApprovalRequest);
    const { factsContent, planSteps } = extractDynamicContent(planApprovalRequest);
    const factsPreview = getFactsPreview(factsContent);

    // Check if this is a "creating plan" state
    const isCreatingPlan = !planSteps.length && !factsContent;

    let stepCounter = 0;

    return (
        <div className={styles.container}>
            {/* Agent Header */}
            <div className={styles.agentHeader}>
                {/* Hide avatar when creating plan */}
                {isCreatingPlan ? (
                    <div className={styles.hiddenAvatar}></div>
                ) : (
                    <div className={styles.agentAvatar}>
                        {getAgentIcon(agentName, null, planApprovalRequest)}
                    </div>
                )}
                <div className={styles.agentInfo}>
                    <Text className={styles.agentName}>
                        {agentName}
                    </Text>
                    {!isCreatingPlan && (
                        <Tag 
                            appearance="brand"
                        >
                            AI Agent
                        </Tag>
                    )}
                </div>
            </div>

            {/* Message Container */}
            <div className={styles.messageContainer}>
                {/* Facts Section */}
                {factsContent && (
                    <div className={styles.factsSection}>
                        <div className={styles.factsHeader}>
                            <div className={styles.factsHeaderLeft}>
                                <CheckmarkCircle20Regular style={{
                                    color: 'var(--colorPaletteGreenForeground1)',
                                    fontSize: '20px',
                                    width: '20px',
                                    height: '20px',
                                    flexShrink: 0
                                }} />
                                <span className={styles.factsTitle}>
                                    Analysis
                                </span>
                            </div>
                            
                            <Button 
                                appearance="secondary" 
                                size="small"
                                onClick={() => setIsFactsExpanded(!isFactsExpanded)}
                                className={styles.factsButton}
                            >
                                {isFactsExpanded ? 'Hide' : 'Details'}
                            </Button>
                        </div>
                        
                        {!isFactsExpanded && (
                            <div className={styles.factsPreview}>
                                {factsPreview}
                            </div>
                        )}
                        
                        {isFactsExpanded && (
                            <div className={styles.factsContent}>
                                {factsContent}
                            </div>
                        )}
                    </div>
                )}

                {/* Plan Title */}
                <div className={styles.planTitle}>
                    {isCreatingPlan ? 'Creating plan...' : `Proposed Plan for ${planApprovalRequest.user_request || 'Task'}`}
                </div>

                {/* Plan Steps */}
                {planSteps.length > 0 && (
                    <div className={styles.stepsList}>
                        {planSteps.map((step, index) => {
                            if (step.type === 'heading') {
                                return (
                                    <div key={index} className={styles.stepHeading}>
                                        {step.text}
                                    </div>
                                );
                            } else {
                                stepCounter++;
                                return (
                                    <div key={index} className={styles.stepItem}>
                                        <div className={styles.stepNumber}>
                                            {stepCounter}
                                        </div>
                                        <div className={styles.stepText}>
                                            {step.text}
                                        </div>
                                    </div>
                                );
                            }
                        })}
                    </div>
                )}

                {/* Instruction Text */}
                {!isCreatingPlan && (
                    <Body1 className={styles.instructionText}>
                        If the plan looks good we can move forward with the first step.
                    </Body1>
                )}

                {/* Action Buttons */}
                {showApprovalButtons && !isCreatingPlan && (
                    <div className={styles.buttonContainer}>
                        <Button
                            appearance="primary"
                            size="medium"
                            onClick={handleApprovePlan}
                            disabled={processingApproval}
                        >
                            {processingApproval ? 'Processing...' : 'Approve Task Plan'}
                        </Button>
                        <Button
                            appearance="secondary"
                            size="medium"
                            onClick={handleRejectPlan}
                            disabled={processingApproval}
                        >
                            Cancel
                        </Button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default renderPlanResponse;