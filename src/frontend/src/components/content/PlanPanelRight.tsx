import React from "react";
import PanelRight from "@/coral/components/Panels/PanelRight";
import TaskDetails from "./TaskDetails";
import { TaskDetailsProps } from "@/models";

const PlanPanelRight: React.FC<TaskDetailsProps> = ({
    planData,
    loading,
    submittingChatDisableInput,
    OnApproveStep,
    processingSubtaskId
}) => {
    // Only show panel when there are tasks created with relevant agents
    // Hide panel during initial streaming or when no steps exist
    const shouldShowPanel = planData && 
                            planData.steps && 
                            planData.steps.length > 0 && 
                            planData.agents && 
                            planData.agents.length > 0 &&
                            !loading;

    if (!shouldShowPanel) {
        return null; // Hide the panel completely
    }

    return (
        <PanelRight
            panelWidth={350}
            defaultClosed={false}
            panelResize={true}
            panelType="first"
        >
            <div>
                <TaskDetails
                    planData={planData}
                    OnApproveStep={OnApproveStep}
                    submittingChatDisableInput={submittingChatDisableInput}
                    processingSubtaskId={processingSubtaskId}
                    loading={loading}
                />
            </div>
        </PanelRight>
    );
};

export default PlanPanelRight;
