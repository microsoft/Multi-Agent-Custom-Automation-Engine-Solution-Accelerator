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

interface SessionTimeoutDialogProps {
  isOpen: boolean;
  onGoHome: () => void;
}

/**
 * Non-dismissible dialog shown when the backend plan approval session times out.
 * No close button, no outside click dismiss, no escape key dismiss.
 */
const SessionTimeoutDialog: React.FC<SessionTimeoutDialogProps> = ({
  isOpen,
  onGoHome,
}) => {
  return (
    <Dialog
      open={isOpen}
      modalType="alert"
      onOpenChange={() => {
        // Prevent any dismiss action (escape key, outside click)
      }}
    >
      <DialogSurface>
        <DialogBody>
          <DialogTitle
            action={null}
          >
            <div className="plan-cancellation-dialog-title">
              <Clock20Regular className="plan-cancellation-warning-icon" />
              Session Timed Out
            </div>
          </DialogTitle>
          <DialogContent>
            Session timed out. Please go back to the home page.
          </DialogContent>
          <DialogActions>
            <Button
              appearance="primary"
              onClick={onGoHome}
            >
              Go To Home
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
};

export default SessionTimeoutDialog;
