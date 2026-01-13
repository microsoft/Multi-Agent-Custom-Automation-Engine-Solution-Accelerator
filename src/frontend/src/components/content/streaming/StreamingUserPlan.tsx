import { MPlanData, ProcessedPlanData } from "@/models";

const getUserPlan = (
    planApprovalRequest: MPlanData | null,
    initialTask?: string,
    planData?: ProcessedPlanData
) => {
    // Check initialTask first
    if (initialTask && initialTask.trim() && initialTask !== 'Task submitted') {
        return initialTask.trim();
    }

    // Check parsed plan data
    if (planApprovalRequest) {
        // Check user_request field
        if (planApprovalRequest.user_request &&
            planApprovalRequest.user_request.trim() &&
            planApprovalRequest.user_request !== 'Plan approval required') {
            return planApprovalRequest.user_request.trim();
        }

        // Check context task
        if (planApprovalRequest.context?.task &&
            planApprovalRequest.context.task.trim() &&
            planApprovalRequest.context.task !== 'Plan approval required') {
            return planApprovalRequest.context.task.trim();
        }
    }

    // Check planData
    if (planData?.plan?.initial_goal &&
        planData.plan.initial_goal.trim() &&
        planData.plan.initial_goal !== 'Task submitted') {
        return planData.plan.initial_goal.trim();
    }

    // Default fallback
    // return 'Please create a plan for me';
};
export default getUserPlan;