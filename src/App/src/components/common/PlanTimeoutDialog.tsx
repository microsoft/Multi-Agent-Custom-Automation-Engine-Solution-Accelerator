import React from 'react';
import {
  Dialog,
  DialogSurface,
  DialogTitle,
  DialogContent,
  DialogBody,
  DialogActions,
  Button,
} from '@fluentui/react-components';
import { Warning20Regular } from '@fluentui/react-icons';
import "../../styles/Panel.css";

interface PlanTimeoutDialogProps {
  isOpen: boolean;
  onGoHome: () => void;
  onCancel: () => void;
}

const PlanTimeoutDialog: React.FC<PlanTimeoutDialogProps> = ({
  isOpen,
  onGoHome,
  onCancel,
}) => {
  return (
    <Dialog open={isOpen}>
      <DialogSurface>
        <DialogBody>
          <DialogTitle>
            <div className="plan-cancellation-dialog-title">
              <Warning20Regular className="plan-cancellation-warning-icon" />
              Session Timed Out
            </div>
          </DialogTitle>
          <DialogContent>
            The plan approval request has timed out because no action was taken.
            Please go to the Home page and create a new task.
          </DialogContent>
          <DialogActions>
            <Button
              appearance="secondary"
              onClick={onCancel}
            >
              Cancel
            </Button>
            <Button
              appearance="primary"
              onClick={onGoHome}
            >
              Go To Home Page
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
};

export default PlanTimeoutDialog;
