import React, { useState } from 'react';
import './App.css';
import AppProvider from './components/AppProvider';
import FluentPlanViewV8 from './components/FluentPlanViewV8';
import {
  Stack,
  Text,
  PrimaryButton,
  TextField,
  IStackStyles,
  ITextStyles,
  Spinner,
  SpinnerSize,
  Card as FluentCard,
  ICardStyles,
  Label,
  DefaultButton,
  mergeStyles
} from '@fluentui/react';

// Define styles
const containerStyles: IStackStyles = {
  root: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '20px',
  }
};

const headerStyles: IStackStyles = {
  root: {
    marginBottom: '20px'
  }
};

const cardStyles: ICardStyles = {
  root: {
    marginBottom: '20px',
  }
};

const titleStyles: ITextStyles = {
  root: {
    fontSize: '28px',
    fontWeight: 600,
    marginBottom: '0',
  }
};

const formStyles: IStackStyles = {
  root: {
    marginTop: '20px',
    marginBottom: '20px'
  }
};

const instructionTextStyles: ITextStyles = {
  root: {
    marginBottom: '8px'
  }
};

const cardTitleStyles: ITextStyles = {
  root: {
    fontSize: '20px',
    fontWeight: 600,
    marginBottom: '16px'
  }
};

function App() {
  const [sessionId, setSessionId] = useState('');
  const [planId, setPlanId] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (sessionId && planId) {
      setLoading(true);
      // Simulate loading
      setTimeout(() => {
        setLoading(false);
        setSubmitted(true);
      }, 500);
    }
  };

  return (
    <AppProvider>
      <Stack styles={containerStyles}>
        <Stack horizontal horizontalAlign="space-between" verticalAlign="center" styles={headerStyles}>
          <Text styles={titleStyles}>
            Multi-Agent Custom Automation Engine
          </Text>
        </Stack>

        {!submitted ? (
          <>
            <FluentCard styles={cardStyles}>
              <Stack tokens={{ padding: 16 }}>
                <Text styles={cardTitleStyles}>Welcome to MACAE</Text>
                <Text styles={instructionTextStyles}>
                  Enter your session ID and plan ID to view your plan and approve/reject steps.
                </Text>
                <Text styles={instructionTextStyles}>
                  These IDs would typically be provided to you when a plan is created by the system.
                </Text>
              </Stack>
            </FluentCard>

            <form onSubmit={handleSubmit}>
              <Stack styles={formStyles} tokens={{ childrenGap: 12 }}>
                <TextField
                  label="Session ID"
                  value={sessionId}
                  onChange={(_, newValue) => setSessionId(newValue || '')}
                  placeholder="Enter Session ID"
                  required
                />
                <TextField
                  label="Plan ID"
                  value={planId}
                  onChange={(_, newValue) => setPlanId(newValue || '')}
                  placeholder="Enter Plan ID"
                  required
                />
                <Stack horizontal tokens={{ childrenGap: 8 }}>
                  <PrimaryButton
                    type="submit"
                    text={loading ? 'Loading...' : 'View Plan'}
                    iconProps={{ iconName: loading ? undefined : 'Forward' }}
                    disabled={loading || !sessionId || !planId}
                  />
                  {loading && <Spinner size={SpinnerSize.small} />}
                </Stack>
              </Stack>
            </form>
          </>
        ) : (
          <FluentPlanViewV8 sessionId={sessionId} planId={planId} />
        )}
      </Stack>
    </AppProvider>
  );
}

export default App;

export default App;
