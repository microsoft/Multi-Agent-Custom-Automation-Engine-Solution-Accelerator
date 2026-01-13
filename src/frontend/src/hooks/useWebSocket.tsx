import { useCallback, useEffect, useRef, useState } from 'react';
import { webSocketService } from '@/services';
import { StreamMessage } from '../models';

export interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  isReconnecting: boolean;
  error: string | null;
}

export const useWebSocket = () => {
  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    isReconnecting: false,
    error: null
  });

  const isConnectedRef = useRef(false);
  const isConnectingRef = useRef(false);
  const lastSessionIdRef = useRef<string | null>(null);
  const lastProcessIdRef = useRef<string | undefined>(undefined);

  const setIsConnecting = useCallback((connecting: boolean) => {
    setState(prev => ({ ...prev, isConnecting: connecting }));
    isConnectingRef.current = connecting;
  }, []);

  const setIsReconnecting = useCallback((reconnecting: boolean) => {
    setState(prev => ({ ...prev, isReconnecting: reconnecting }));
  }, []);

  const connectWebSocket = useCallback(async (sessionId: string, processId?: string) => {
    if (isConnectedRef.current || isConnectingRef.current) return;

    setIsConnecting(true);
    lastSessionIdRef.current = sessionId;
    lastProcessIdRef.current = processId;

    try {
      await webSocketService.connect(sessionId, processId);
      isConnectedRef.current = true;
      setState(prev => ({
        ...prev,
        isConnected: true,
        isConnecting: false,
        error: null
      }));
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      isConnectedRef.current = false;
      isConnectingRef.current = false;
      setState(prev => ({
        ...prev,
        isConnected: false,
        isConnecting: false,
        error: 'Failed to connect to server'
      }));
    }
  }, [setIsConnecting]);

  const reconnect = useCallback(async () => {
    if (!lastSessionIdRef.current) return;

    setIsReconnecting(true);
    try {
      await webSocketService.connect(lastSessionIdRef.current, lastProcessIdRef.current);
      isConnectedRef.current = true;
      setState(prev => ({
        ...prev,
        isConnected: true,
        isReconnecting: false,
        error: null
      }));
    } catch (error) {
      console.error('Failed to reconnect to WebSocket:', error);
      isConnectedRef.current = false;
      setState(prev => ({
        ...prev,
        isConnected: false,
        isReconnecting: false,
        error: 'Failed to reconnect to server'
      }));
    }
  }, [setIsReconnecting]);

  const disconnect = useCallback(() => {
    webSocketService.disconnect();
    isConnectedRef.current = false;
    isConnectingRef.current = false;
    setState(prev => ({
      ...prev,
      isConnected: false,
      isConnecting: false,
      isReconnecting: false
    }));
  }, []);

  useEffect(() => {
    // Set up connection status listener
    const unsubscribeStatus = webSocketService.on('connection_status', (message: StreamMessage) => {
      if (message.data?.connected !== undefined) {
        const connected = message.data.connected;
        isConnectedRef.current = connected;
        setState(prev => ({
          ...prev,
          isConnected: connected,
          isConnecting: false,
          isReconnecting: false,
          error: connected ? null : prev.error
        }));
      }
    });

    // Set up error listener
    const unsubscribeError = webSocketService.on('error', (message: StreamMessage) => {
      isConnectedRef.current = false;
      setState(prev => ({
        ...prev,
        isConnected: false,
        error: message.data?.error || 'WebSocket error occurred'
      }));
    });

    // Cleanup on unmount
    return () => {
      unsubscribeStatus();
      unsubscribeError();
      disconnect();
    };
  }, [disconnect]);

  return {
    ...state,
    connect: connectWebSocket,
    disconnect,
    reconnect,
    webSocketService
  };
};