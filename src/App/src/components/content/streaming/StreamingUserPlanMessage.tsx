import { PersonRegular } from "@fluentui/react-icons";
import getUserTask from "./StreamingUserPlan";
import { MPlanData, ProcessedPlanData } from "@/models";

// Render user task message with exact styling from image
const renderUserPlanMessage = (planApprovalRequest: MPlanData | null,
    initialTask?: string,
    planData?: ProcessedPlanData) => {
    const userPlan = getUserTask(planApprovalRequest, initialTask, planData);

    if (!userPlan) return null;

    return (
        <div style={{
            maxWidth: '800px',
            margin: '0 auto 32px auto',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '16px',
            flexDirection: 'row-reverse'
        }}>
            {/* User Avatar */}
            <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                backgroundColor: 'var(--colorBrandBackground)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
            }}>
                <PersonRegular style={{ fontSize: '16px', color: 'white' }} />
            </div>

            {/* User Message */}
            <div style={{
                flex: 1,
                maxWidth: 'calc(100% - 48px)',
                display: 'flex',
                justifyContent: 'flex-end'
            }}>
                <div style={{
                    backgroundColor: 'var(--colorBrandBackground)',
                    color: 'white',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    fontSize: '14px',
                    lineHeight: '1.5',
                    wordWrap: 'break-word',
                    maxWidth: '80%'
                }}>
                    {userPlan}
                </div>
            </div>
        </div>
    );
};

export default renderUserPlanMessage;