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
import { Clock20Regular } from '@fluentui/react-icons';
import "../../styles/Panel.css";

interface TimeoutDialogProps {
  isOpen: boolean;
  message: string;
  onGoHome: () => void;
}

/**
 * Dialog shown when the backend sends a timeout notification
 * (e.g., plan approval timed out).
 */
const TimeoutDialog: React.FC<TimeoutDialogProps> = ({ isOpen, message, onGoHome }) => (
  <Dialog open={isOpen} modalType="alert">
    <DialogSurface>
      <DialogBody>
        <DialogTitle>
          <div className="plan-cancellation-dialog-title">
            <Clock20Regular className="plan-cancellation-warning-icon" />
            Session Timed Out
          </div>
        </DialogTitle>
        <DialogContent>
          {message}
        </DialogContent>
        <DialogActions>
          <Button appearance="primary" onClick={onGoHome}>
            Go to Home
          </Button>
        </DialogActions>
      </DialogBody>
    </DialogSurface>
  </Dialog>
);

export default TimeoutDialog;
