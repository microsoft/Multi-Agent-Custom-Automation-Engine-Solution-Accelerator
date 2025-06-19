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
    if (!planData) return null;

    return (
        <PanelRight
            panelWidth={350}
            defaultClosed={false}
            panelResize={true}
            panelType="first"
        >

            <div >
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
