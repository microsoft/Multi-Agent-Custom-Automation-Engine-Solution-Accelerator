import React from "react";

import { Button } from "@fluentui/react-components";
import { History20Filled, MoreHorizontalRegular, TaskListSquareLtr20Regular, TaskListSquareLtrFilled } from "@fluentui/react-icons";
import PanelRight from "@/coral/components/Panels/PanelRight";
import PanelRightToolbar from "@/coral/components/Panels/PanelRightToolbar";
import TaskDetails from "./TaskDetails";
import { TaskDetailsProps } from "@/models";


const PlanPanelRight: React.FC<TaskDetailsProps> = ({
    planData,
    loading,
    OnApproveStep,
    OnRejectStep,
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
                    OnRejectStep={OnRejectStep}
                    processingSubtaskId={processingSubtaskId}
                    loading={loading}
                />
            </div>
        </PanelRight>
    );
};

export default PlanPanelRight;
