import { useCallback } from 'react';
import { PlanStatus } from '../models';
import { APIService } from '../api/apiService';

interface UsePlanCancellationAlertProps {
  planData: any;
  planApprovalRequest: any;
  onNavigate: () => void;
}

/**
 * Custom hook to handle plan cancellation alerts when navigating during active plans
 */
export const usePlanCancellationAlert = ({
  planData,
  planApprovalRequest,
  onNavigate
}: UsePlanCancellationAlertProps) => {
  const apiService = new APIService();

  /**
   * Check if a plan is currently active/running
   */
  const isPlanActive = useCallback(() => {
    return planData?.plan?.overall_status === PlanStatus.IN_PROGRESS;
  }, [planData]);

  /**
   * Handle the confirmation dialog and plan cancellation
   */
  const handleNavigationWithConfirmation = useCallback(async () => {
    if (!isPlanActive()) {
      // Plan is not active, proceed with navigation
      onNavigate();
      return;
    }

    // Show confirmation dialog
    const userConfirmed = window.confirm(
      "If you continue, the plan process will be stopped and the plan will be cancelled."
    );

    if (!userConfirmed) {
      // User cancelled, do nothing
      return;
    }

    try {
      // User confirmed, cancel the plan
      if (planApprovalRequest?.id) {
        await apiService.approvePlan({
          m_plan_id: planApprovalRequest.id,
          plan_id: planData?.plan?.id,
          approved: false,
          feedback: 'Plan cancelled by user navigation'
        });
      }

      // Navigate after successful cancellation
      onNavigate();
    } catch (error) {
      console.error('❌ Failed to cancel plan:', error);
      // Show error but still allow navigation
      alert('Failed to cancel the plan properly, but navigation will continue.');
      onNavigate();
    }
  }, [isPlanActive, onNavigate, planApprovalRequest, planData, apiService]);

  return {
    isPlanActive,
    handleNavigationWithConfirmation
  };
};

export default usePlanCancellationAlert;