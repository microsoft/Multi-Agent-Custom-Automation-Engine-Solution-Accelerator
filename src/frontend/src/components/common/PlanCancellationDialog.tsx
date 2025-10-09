import React from 'react';
import {
  Dialog,
  DialogTrigger,
  DialogSurface,
  DialogTitle,
  DialogContent,
  DialogBody,
  DialogActions,
  Button,
} from '@fluentui/react-components';
import { Warning20Regular } from '@fluentui/react-icons';
import "../../styles/Panel.css";

interface PlanCancellationDialogProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

/**
 * Confirmation dialog for plan cancellation when navigating during active plans
 */
const PlanCancellationDialog: React.FC<PlanCancellationDialogProps> = ({
  isOpen,
  onConfirm,
  onCancel,
  loading = false
}) => {
  return (
    <Dialog open={isOpen} onOpenChange={(_, data) => !data.open && onCancel()}>
      <DialogSurface>
        <DialogBody>
          <DialogTitle>
            <div className="plan-cancellation-dialog-title">
              <Warning20Regular className="plan-cancellation-warning-icon" />
              Confirm Plan Cancellation
            </div>
          </DialogTitle>
          <DialogContent>
            If you continue, the plan process will be stopped and the plan will be cancelled.
          </DialogContent>
          <DialogActions>
            <DialogTrigger disableButtonEnhancement>
              <Button 
                appearance="secondary" 
                onClick={onCancel}
                disabled={loading}
              >
                Cancel
              </Button>
            </DialogTrigger>
            <Button 
              appearance="primary" 
              onClick={onConfirm}
              disabled={loading}
            >
              {loading ? 'Cancelling...' : 'Yes'}
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
};

export default PlanCancellationDialog;