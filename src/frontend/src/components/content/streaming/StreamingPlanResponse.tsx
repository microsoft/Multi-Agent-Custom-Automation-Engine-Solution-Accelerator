import { MPlanData } from "@/models";
import {
    Button,
    Text,
    Body1,
    Tag,
    makeStyles,
    tokens,
} from "@fluentui/react-components";
import { CheckmarkCircle20Regular } from "@fluentui/react-icons";
import React, { useState, useMemo, useCallback } from "react";
import { getAgentIcon, getAgentDisplayName } from "@/utils/agentIconUtils";

// ─── Types ───────────────────────────────────────────────────────────────────

/** A single plan step (heading or numbered substep) */
export interface PlanStep {
    type: "heading" | "substep";
    text: string;
}

/** Props for the top-level PlanResponse component */
export interface PlanResponseProps {
    planApprovalRequest: MPlanData | null;
    handleApprovePlan: () => void;
    handleRejectPlan: () => void;
    processingApproval: boolean;
    showApprovalButtons: boolean;
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const useStyles = makeStyles({
    container: {
        maxWidth: "800px",
        margin: "0 auto 32px auto",
        padding: "0 24px",
        fontFamily: tokens.fontFamilyBase,
    },
    agentHeader: {
        display: "flex",
        alignItems: "center",
        gap: "16px",
        marginBottom: "8px",
    },
    agentAvatar: {
        width: "32px",
        height: "32px",
        borderRadius: "50%",
        backgroundColor: "var(--colorNeutralBackground3)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
    },
    hiddenAvatar: {
        width: "32px",
        height: "32px",
        visibility: "hidden",
        flexShrink: 0,
    },
    agentInfo: {
        display: "flex",
        alignItems: "center",
        gap: "12px",
        flex: 1,
    },
    agentName: {
        fontSize: "14px",
        fontWeight: "600",
        color: "var(--colorNeutralForeground1)",
        lineHeight: "20px",
    },
    messageContainer: {
        backgroundColor: "var(--colorNeutralBackground2)",
        padding: "12px 16px",
        borderRadius: "8px",
        fontSize: "14px",
        lineHeight: "1.5",
        wordWrap: "break-word",
    },
    factsSection: {
        backgroundColor: "var(--colorNeutralBackground2)",
        border: "1px solid var(--colorNeutralStroke2)",
        borderRadius: "8px",
        padding: "16px",
        marginBottom: "16px",
    },
    factsHeader: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "12px",
    },
    factsHeaderLeft: {
        display: "flex",
        alignItems: "center",
        gap: "12px",
    },
    factsTitle: {
        fontWeight: "500",
        color: "var(--colorNeutralForeground1)",
        fontSize: "14px",
        lineHeight: "20px",
    },
    factsButton: {
        backgroundColor: "var(--colorNeutralBackground3)",
        border: "1px solid var(--colorNeutralStroke2)",
        borderRadius: "16px",
        padding: "4px 12px",
        fontSize: "14px",
        fontWeight: "500",
        cursor: "pointer",
    },
    factsPreview: {
        fontSize: "14px",
        lineHeight: "1.4",
        color: "var(--colorNeutralForeground2)",
        marginTop: "8px",
    },
    factsContent: {
        fontSize: "14px",
        lineHeight: "1.5",
        color: "var(--colorNeutralForeground2)",
        marginTop: "8px",
        whiteSpace: "pre-wrap",
    },
    planTitle: {
        marginBottom: "20px",
        fontSize: "18px",
        fontWeight: "600",
        color: "var(--colorNeutralForeground1)",
        lineHeight: "24px",
    },
    stepsList: {
        marginBottom: "16px",
    },
    stepItem: {
        display: "flex",
        alignItems: "flex-start",
        gap: "12px",
        marginBottom: "12px",
    },
    stepNumber: {
        minWidth: "24px",
        height: "24px",
        borderRadius: "50%",
        backgroundColor: "var(--colorNeutralBackground3)",
        border: "1px solid var(--colorNeutralStroke2)",
        color: "var(--colorNeutralForeground1)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "12px",
        fontWeight: "600",
        flexShrink: 0,
        marginTop: "2px",
    },
    stepText: {
        fontSize: "14px",
        color: "var(--colorNeutralForeground1)",
        lineHeight: "1.5",
        flex: 1,
        wordWrap: "break-word",
        overflowWrap: "break-word",
    },
    stepHeading: {
        marginBottom: "12px",
        fontSize: "16px",
        fontWeight: "600",
        color: "var(--colorNeutralForeground1)",
        lineHeight: "22px",
    },
    instructionText: {
        color: "var(--colorNeutralForeground2)",
        fontSize: "14px",
        lineHeight: "1.5",
        marginBottom: "16px",
    },
    buttonContainer: {
        display: "flex",
        gap: "12px",
        alignItems: "center",
        marginTop: "20px",
    },
});

// ─── Utility helpers ─────────────────────────────────────────────────────────

/** Get agent display name from the first step in the plan approval request */
const getAgentDisplayNameFromPlan = (planApprovalRequest: MPlanData | null): string => {
    if (planApprovalRequest?.steps?.length) {
        const firstAgent = planApprovalRequest.steps.find((step) => step.agent)?.agent;
        if (firstAgent) {
            return getAgentDisplayName(firstAgent);
        }
    }
    return getAgentDisplayName("Planning Agent");
};

/** Dynamically extract facts + plan steps from the approval request */
const extractDynamicContent = (
    planApprovalRequest: MPlanData
): { factsContent: string; planSteps: PlanStep[] } => {
    if (!planApprovalRequest) return { factsContent: "", planSteps: [] };

    const factsSources: string[] = [];
    let planSteps: PlanStep[] = [];

    if (
        planApprovalRequest.context?.participant_descriptions &&
        Object.keys(planApprovalRequest.context.participant_descriptions).length > 0
    ) {
        let teamContent = "Team Assembly:\n\n";
        Object.entries(planApprovalRequest.context.participant_descriptions).forEach(
            ([agent, description]) => {
                teamContent += `${agent}: ${description}\n\n`;
            }
        );
        factsSources.push(teamContent);
    }

    if (planApprovalRequest.facts && planApprovalRequest.facts.trim().length > 10) {
        factsSources.push(planApprovalRequest.facts.trim());
    }

    const factsContent = factsSources.join("\n---\n\n");

    if (planApprovalRequest.steps && planApprovalRequest.steps.length > 0) {
        planApprovalRequest.steps.forEach((step) => {
            const action = step.action || step.cleanAction || "";
            if (action.trim()) {
                planSteps.push({
                    type: action.trim().endsWith(":") ? "heading" : "substep",
                    text: action.trim(),
                });
            }
        });
    }

    if (planSteps.length === 0) {
        const searchContent = planApprovalRequest.user_request || planApprovalRequest.facts || "";
        const lines = searchContent.split("\n");

        for (const line of lines) {
            const trimmedLine = line.trim();
            if (
                !trimmedLine ||
                trimmedLine.toLowerCase().includes("plan created") ||
                trimmedLine.toLowerCase().includes("user request") ||
                trimmedLine.toLowerCase().includes("team assembly") ||
                trimmedLine.toLowerCase().includes("fact sheet")
            ) {
                continue;
            }

            if (
                trimmedLine.match(/^[-•*]\s+/) ||
                trimmedLine.match(/^\d+\.\s+/) ||
                trimmedLine.match(/^[a-zA-Z][\w\s]*:$/)
            ) {
                let cleanText = trimmedLine
                    .replace(/^[-•*]\s+/, "")
                    .replace(/^\d+\.\s+/, "")
                    .trim();

                if (cleanText.length > 3) {
                    planSteps.push({
                        type: cleanText.endsWith(":") ? "heading" : "substep",
                        text: cleanText,
                    });
                }
            }
        }
    }

    return { factsContent, planSteps };
};

/** Truncate facts content for preview */
const getFactsPreview = (content: string): string => {
    if (!content) return "";
    return content.length > 200 ? content.substring(0, 200) + "..." : content;
};

// ─── Sub-components ──────────────────────────────────────────────────────────

/** Props for the FactsSection sub-component */
interface FactsSectionProps {
    factsContent: string;
}

/**
 * Collapsible "Analysis" section showing extracted facts.
 */
const FactsSection: React.FC<FactsSectionProps> = React.memo(({ factsContent }) => {
    const styles = useStyles();
    const [isExpanded, setIsExpanded] = useState(false);
    const preview = useMemo(() => getFactsPreview(factsContent), [factsContent]);
    const toggleExpanded = useCallback(() => setIsExpanded(prev => !prev), []);

    return (
        <div className={styles.factsSection}>
            <div className={styles.factsHeader}>
                <div className={styles.factsHeaderLeft}>
                    <CheckmarkCircle20Regular
                        style={{
                            color: "var(--colorPaletteGreenForeground1)",
                            fontSize: "20px",
                            width: "20px",
                            height: "20px",
                            flexShrink: 0,
                        }}
                    />
                    <span className={styles.factsTitle}>Analysis</span>
                </div>
                <Button
                    appearance="secondary"
                    size="small"
                    onClick={toggleExpanded}
                    className={styles.factsButton}
                >
                    {isExpanded ? "Hide" : "Details"}
                </Button>
            </div>
            {!isExpanded && <div className={styles.factsPreview}>{preview}</div>}
            {isExpanded && <div className={styles.factsContent}>{factsContent}</div>}
        </div>
    );
});
FactsSection.displayName = 'FactsSection';

/** Props for the PlanStepsList sub-component */
interface PlanStepsListProps {
    steps: PlanStep[];
}

/**
 * Renders the numbered list of plan steps with optional headings.
 */
const PlanStepsList: React.FC<PlanStepsListProps> = React.memo(({ steps }) => {
    const styles = useStyles();
    let stepCounter = 0;

    return (
        <div className={styles.stepsList}>
            {steps.map((step, index) => {
                if (step.type === "heading") {
                    return (
                        <div key={index} className={styles.stepHeading}>
                            {step.text}
                        </div>
                    );
                }
                stepCounter++;
                return (
                    <div key={index} className={styles.stepItem}>
                        <div className={styles.stepNumber}>{stepCounter}</div>
                        <div className={styles.stepText}>{step.text}</div>
                    </div>
                );
            })}
        </div>
    );
});
PlanStepsList.displayName = 'PlanStepsList';

/** Props for the ApprovalActions sub-component */
interface ApprovalActionsProps {
    handleApprovePlan: () => void;
    handleRejectPlan: () => void;
    processingApproval: boolean;
}

/**
 * Approve / Cancel buttons for plan approval.
 */
const ApprovalActions: React.FC<ApprovalActionsProps> = React.memo(({
    handleApprovePlan,
    handleRejectPlan,
    processingApproval,
}) => {
    const styles = useStyles();

    return (
        <div className={styles.buttonContainer}>
            <Button
                appearance="primary"
                size="medium"
                onClick={handleApprovePlan}
                disabled={processingApproval}
            >
                {processingApproval ? "Processing..." : "Approve Task Plan"}
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
    );
});
ApprovalActions.displayName = 'ApprovalActions';

// ─── Main Component ──────────────────────────────────────────────────────────

/**
 * Renders the plan response card with agent header, facts, steps, and approval buttons.
 * Handles a single message type: plan approval response.
 */
const PlanResponse: React.FC<PlanResponseProps> = React.memo(({
    planApprovalRequest,
    handleApprovePlan,
    handleRejectPlan,
    processingApproval,
    showApprovalButtons,
}) => {
    const styles = useStyles();

    const agentName = useMemo(
        () => planApprovalRequest ? getAgentDisplayNameFromPlan(planApprovalRequest) : "",
        [planApprovalRequest]
    );
    const { factsContent, planSteps } = useMemo(
        () => planApprovalRequest ? extractDynamicContent(planApprovalRequest) : { factsContent: "", planSteps: [] as PlanStep[] },
        [planApprovalRequest]
    );
    const isCreatingPlan = !planSteps.length && !factsContent;

    if (!planApprovalRequest) return null;

    return (
        <div className={styles.container}>
            {/* Agent Header */}
            <div className={styles.agentHeader}>
                {isCreatingPlan ? (
                    <div className={styles.hiddenAvatar} />
                ) : (
                    <div className={styles.agentAvatar}>
                        {getAgentIcon(agentName, null, planApprovalRequest)}
                    </div>
                )}
                <div className={styles.agentInfo}>
                    <Text className={styles.agentName}>{agentName}</Text>
                    {!isCreatingPlan && <Tag appearance="brand">AI Agent</Tag>}
                </div>
            </div>

            {/* Message Container */}
            <div className={styles.messageContainer}>
                {factsContent && <FactsSection factsContent={factsContent} />}

                <div className={styles.planTitle}>
                    {isCreatingPlan
                        ? "Creating plan..."
                        : `Proposed Plan for ${planApprovalRequest.user_request || "Task"}`}
                </div>

                {planSteps.length > 0 && <PlanStepsList steps={planSteps} />}

                {!isCreatingPlan && (
                    <Body1 className={styles.instructionText}>
                        If the plan looks good we can move forward with the first step.
                    </Body1>
                )}

                {showApprovalButtons && !isCreatingPlan && (
                    <ApprovalActions
                        handleApprovePlan={handleApprovePlan}
                        handleRejectPlan={handleRejectPlan}
                        processingApproval={processingApproval}
                    />
                )}
            </div>
        </div>
    );
});
PlanResponse.displayName = 'PlanResponse';

// ─── Backward-compatible render function (deprecated) ────────────────────────

/** @deprecated Use `<PlanResponse>` component instead */
const renderPlanResponse = (
    planApprovalRequest: MPlanData | null,
    handleApprovePlan: () => void,
    handleRejectPlan: () => void,
    processingApproval: boolean,
    showApprovalButtons: boolean
) => (
    <PlanResponse
        planApprovalRequest={planApprovalRequest}
        handleApprovePlan={handleApprovePlan}
        handleRejectPlan={handleRejectPlan}
        processingApproval={processingApproval}
        showApprovalButtons={showApprovalButtons}
    />
);

export { PlanResponse, FactsSection, PlanStepsList, ApprovalActions };
export default renderPlanResponse;