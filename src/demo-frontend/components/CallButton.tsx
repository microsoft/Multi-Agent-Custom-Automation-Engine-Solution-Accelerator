'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';

/**
 * Call state for tracking the current call status
 */
export type CallState = 'idle' | 'connecting' | 'ringing' | 'connected' | 'ended' | 'error';

/**
 * Call event data structure
 */
export interface CallEvent {
  /** Event type */
  type: 'state_change' | 'transcript' | 'error';
  /** Call state (for state_change events) */
  state?: CallState;
  /** Transcript text (for transcript events) */
  transcript?: string;
  /** Error message (for error events) */
  error?: string;
  /** Timestamp of the event */
  timestamp: Date;
}

/**
 * Props for the CallButton component
 */
export interface CallButtonProps {
  /** Twilio phone number to call (overrides env variable) */
  phoneNumber?: string;
  /** WebSocket URL for voice connection (overrides env variable) */
  websocketUrl?: string;
  /** Whether the component is in a loading state */
  loading?: boolean;
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Callback when call state changes */
  onCallStateChange?: (state: CallState) => void;
  /** Callback when a call event occurs */
  onCallEvent?: (event: CallEvent) => void;
  /** Label for the button */
  label?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Optional className for custom styling */
  className?: string;
}

/**
 * Phone icon for idle state
 */
const PhoneIcon = ({ className = 'h-6 w-6' }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
  </svg>
);

/**
 * Phone off icon for ending call
 */
const PhoneOffIcon = ({ className = 'h-6 w-6' }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-3.33-2.67m-2.67-3.34a19.79 19.79 0 0 1-3.07-8.63A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91" />
    <line x1="1" x2="23" y1="1" y2="23" />
  </svg>
);

/**
 * Connecting/loading spinner icon
 */
const SpinnerIcon = ({ className = 'h-6 w-6' }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className={`${className} animate-spin`}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <circle className="opacity-25" cx="12" cy="12" r="10" />
    <path className="opacity-75" d="M4 12a8 8 0 0 1 8-8" />
  </svg>
);

/**
 * Voice wave icon for connected state
 */
const VoiceWaveIcon = ({ className = 'h-6 w-6' }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" x2="12" y1="19" y2="22" />
  </svg>
);

/**
 * State-specific configuration
 */
interface StateConfig {
  icon: React.ReactNode;
  label: string;
  className: string;
  ariaLabel: string;
}

/**
 * Get configuration for each call state
 */
function getStateConfig(
  state: CallState,
  customLabel?: string,
  iconSize: string = 'h-6 w-6'
): StateConfig {
  const configs: Record<CallState, StateConfig> = {
    idle: {
      icon: <PhoneIcon className={iconSize} />,
      label: customLabel || 'Call Now',
      className: 'bg-brand hover:bg-brand-dark text-white',
      ariaLabel: 'Start a call with the AI assistant',
    },
    connecting: {
      icon: <SpinnerIcon className={iconSize} />,
      label: 'Connecting...',
      className: 'bg-amber-500 text-white cursor-wait',
      ariaLabel: 'Connecting to the AI assistant',
    },
    ringing: {
      icon: <PhoneIcon className={`${iconSize} animate-pulse`} />,
      label: 'Ringing...',
      className: 'bg-amber-500 text-white',
      ariaLabel: 'Ringing, please wait',
    },
    connected: {
      icon: <VoiceWaveIcon className={iconSize} />,
      label: 'Connected',
      className: 'bg-green-500 hover:bg-red-500 text-white',
      ariaLabel: 'Call connected, click to end call',
    },
    ended: {
      icon: <PhoneIcon className={iconSize} />,
      label: customLabel || 'Call Again',
      className: 'bg-brand hover:bg-brand-dark text-white',
      ariaLabel: 'Start a new call',
    },
    error: {
      icon: <PhoneOffIcon className={iconSize} />,
      label: 'Try Again',
      className: 'bg-red-500 hover:bg-red-600 text-white',
      ariaLabel: 'Call failed, click to try again',
    },
  };

  return configs[state];
}

/**
 * Size configurations
 */
const SIZE_CONFIGS = {
  sm: {
    button: 'px-4 py-2 text-sm',
    icon: 'h-4 w-4',
    pulse: 'h-10 w-32',
  },
  md: {
    button: 'px-6 py-3 text-base',
    icon: 'h-6 w-6',
    pulse: 'h-12 w-40',
  },
  lg: {
    button: 'px-8 py-4 text-lg',
    icon: 'h-8 w-8',
    pulse: 'h-14 w-48',
  },
};

/**
 * Skeleton component for loading state
 */
const CallButtonSkeleton: React.FC<{ size: 'sm' | 'md' | 'lg' }> = ({ size }) => (
  <div
    className={`animate-pulse bg-muted rounded-lg ${SIZE_CONFIGS[size].pulse}`}
    role="status"
    aria-label="Loading call button"
  />
);

/**
 * Format call duration (seconds to MM:SS)
 */
function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * CallButton component for Twilio click-to-call integration
 *
 * Provides a button that initiates voice calls through Twilio to connect
 * with the AI voice assistant. Supports multiple visual states and
 * real-time call status updates.
 *
 * @example
 * ```tsx
 * <CallButton
 *   onCallStateChange={(state) => console.log('Call state:', state)}
 *   label="Talk to AI Assistant"
 *   size="lg"
 * />
 * ```
 */
const CallButton: React.FC<CallButtonProps> = ({
  phoneNumber,
  websocketUrl,
  loading = false,
  disabled = false,
  onCallStateChange,
  onCallEvent,
  label,
  size = 'md',
  className = '',
}) => {
  const [callState, setCallState] = useState<CallState>('idle');
  const [callDuration, setCallDuration] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Refs for WebSocket and timer
  const wsRef = useRef<WebSocket | null>(null);
  const durationTimerRef = useRef<NodeJS.Timeout | null>(null);
  const callStateRef = useRef<CallState>('idle');

  // Get phone number from env or prop
  const twilioNumber = phoneNumber || process.env.NEXT_PUBLIC_TWILIO_NUMBER;
  const wsUrl = websocketUrl || process.env.NEXT_PUBLIC_VOICE_WEBSOCKET_URL;

  // Size configuration
  const sizeConfig = SIZE_CONFIGS[size];

  /**
   * Emit a call event
   */
  const emitEvent = useCallback(
    (type: CallEvent['type'], data?: Partial<CallEvent>) => {
      const event: CallEvent = {
        type,
        timestamp: new Date(),
        ...data,
      };
      onCallEvent?.(event);
    },
    [onCallEvent]
  );

  /**
   * Update call state and notify listeners
   */
  const updateCallState = useCallback(
    (newState: CallState) => {
      callStateRef.current = newState;
      setCallState(newState);
      onCallStateChange?.(newState);
      emitEvent('state_change', { state: newState });
    },
    [onCallStateChange, emitEvent]
  );

  /**
   * Start the call duration timer
   */
  const startDurationTimer = useCallback(() => {
    setCallDuration(0);
    durationTimerRef.current = setInterval(() => {
      setCallDuration((prev) => prev + 1);
    }, 1000);
  }, []);

  /**
   * Stop the call duration timer
   */
  const stopDurationTimer = useCallback(() => {
    if (durationTimerRef.current) {
      clearInterval(durationTimerRef.current);
      durationTimerRef.current = null;
    }
  }, []);

  /**
   * Clean up WebSocket connection
   */
  const cleanupWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  /**
   * Initiate a call via WebSocket
   */
  const startCall = useCallback(async () => {
    if (!wsUrl) {
      setErrorMessage('Voice WebSocket URL not configured');
      updateCallState('error');
      emitEvent('error', { error: 'Voice WebSocket URL not configured' });
      return;
    }

    try {
      updateCallState('connecting');
      setErrorMessage(null);

      // Connect to voice WebSocket server
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        updateCallState('ringing');

        // Send call initiation message
        ws.send(
          JSON.stringify({
            type: 'call_start',
            phoneNumber: twilioNumber,
            timestamp: new Date().toISOString(),
          })
        );
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case 'call_connected':
              updateCallState('connected');
              startDurationTimer();
              break;

            case 'call_ended':
              stopDurationTimer();
              updateCallState('ended');
              cleanupWebSocket();
              break;

            case 'transcript':
              emitEvent('transcript', { transcript: data.text });
              break;

            case 'error':
              setErrorMessage(data.message || 'An error occurred');
              stopDurationTimer();
              updateCallState('error');
              emitEvent('error', { error: data.message });
              cleanupWebSocket();
              break;

            default:
              // Handle other message types
              break;
          }
        } catch {
          // Non-JSON message, ignore
        }
      };

      ws.onerror = () => {
        setErrorMessage('Connection error. Please try again.');
        stopDurationTimer();
        updateCallState('error');
        emitEvent('error', { error: 'WebSocket connection error' });
      };

      ws.onclose = () => {
        const currentState = callStateRef.current;
        if (
          currentState === 'connected' ||
          currentState === 'ringing' ||
          currentState === 'connecting'
        ) {
          stopDurationTimer();
          updateCallState('ended');
        }
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start call';
      setErrorMessage(message);
      updateCallState('error');
      emitEvent('error', { error: message });
    }
  }, [
    wsUrl,
    twilioNumber,
    updateCallState,
    emitEvent,
    startDurationTimer,
    stopDurationTimer,
    cleanupWebSocket,
  ]);

  /**
   * End the current call
   */
  const endCall = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'call_end',
          timestamp: new Date().toISOString(),
        })
      );
    }

    stopDurationTimer();
    cleanupWebSocket();
    updateCallState('ended');
  }, [stopDurationTimer, cleanupWebSocket, updateCallState]);

  /**
   * Handle button click based on current state
   */
  const handleClick = useCallback(() => {
    if (disabled) return;

    switch (callState) {
      case 'idle':
      case 'ended':
      case 'error':
        startCall();
        break;

      case 'connected':
      case 'ringing':
      case 'connecting':
        endCall();
        break;

      default:
        break;
    }
  }, [callState, disabled, startCall, endCall]);

  /**
   * Handle keyboard interaction for accessibility
   */
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleClick();
      }
    },
    [handleClick]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopDurationTimer();
      cleanupWebSocket();
    };
  }, [stopDurationTimer, cleanupWebSocket]);

  // Get state configuration
  const stateConfig = getStateConfig(callState, label, sizeConfig.icon);

  if (loading) {
    return <CallButtonSkeleton size={size} />;
  }

  // Determine if button is in an active call state
  const isActiveCall = callState === 'connected' || callState === 'ringing' || callState === 'connecting';

  return (
    <div className={`inline-flex flex-col items-center gap-2 ${className}`}>
      <button
        type="button"
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        disabled={disabled || callState === 'connecting'}
        className={`
          inline-flex items-center justify-center gap-2 rounded-lg font-medium
          transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2
          disabled:opacity-50 disabled:cursor-not-allowed
          ${sizeConfig.button}
          ${stateConfig.className}
          ${isActiveCall ? 'ring-2 ring-offset-2 ring-current animate-pulse' : ''}
        `}
        aria-label={stateConfig.ariaLabel}
        aria-live="polite"
        aria-busy={callState === 'connecting'}
      >
        {stateConfig.icon}
        <span>{stateConfig.label}</span>
        {callState === 'connected' && (
          <span className="ml-2 font-mono text-sm opacity-90">
            {formatDuration(callDuration)}
          </span>
        )}
      </button>

      {/* Error message display */}
      {errorMessage && callState === 'error' && (
        <p className="text-sm text-red-500" role="alert">
          {errorMessage}
        </p>
      )}

      {/* Phone number display */}
      {twilioNumber && callState === 'idle' && (
        <p className="text-xs text-muted-foreground">
          Call {twilioNumber}
        </p>
      )}

      {/* Connected status indicator */}
      {callState === 'connected' && (
        <div className="flex items-center gap-1.5 text-xs text-green-600">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
          </span>
          <span>Call in progress</span>
        </div>
      )}
    </div>
  );
};

export default CallButton;
