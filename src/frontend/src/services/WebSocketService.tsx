import { headerBuilder } from '../api/config';

export interface StreamMessage {
    type: 'plan_update' | 'step_update' | 'agent_message' | 'error' | 'connection_status' | 'plan_approval_request' | 'final_result';
    plan_id?: string;
    session_id?: string;
    data?: any;
    timestamp?: string;
}

export interface StreamingPlanUpdate {
    plan_id: string;
    session_id?: string;
    step_id?: string;
    agent_name?: string;
    content?: string;
    status?: 'in_progress' | 'completed' | 'error' | 'creating_plan' | 'pending_approval';
    message_type?: 'thinking' | 'action' | 'result' | 'clarification_needed' | 'plan_approval_request';
    timestamp?: number;
}

export interface PlanApprovalRequestData {
    plan_id: string;
    session_id: string;
    plan: {
        steps: Array<{
            id: string;
            description: string;
            agent: string;
            estimated_duration?: string;
        }>;
        total_steps: number;
        estimated_completion?: string;
    };
    status: 'PENDING_APPROVAL';
}

export interface PlanApprovalResponseData {
    plan_id: string;
    session_id: string;
    approved: boolean;
    feedback?: string;
}

class WebSocketService {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 12000;
    private listeners: Map<string, Set<(message: StreamMessage) => void>> = new Map();
    private planSubscriptions: Set<string> = new Set();
    private reconnectTimer: NodeJS.Timeout | null = null;
    private isConnecting = false;

    /**
     * Connect to WebSocket server
     */
    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            if (this.isConnecting) {
                console.log('Connection attempt already in progress');
                resolve();
                return;
            }

            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }

            try {
                this.isConnecting = true;
                
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsHost = process.env.REACT_APP_WS_HOST || '127.0.0.1:8000';
                const processId = crypto.randomUUID();

                const authHeaders = headerBuilder();
                const userId = authHeaders['x-ms-client-principal-id'];
                
                if (!userId) {
                    console.error('No user ID available for WebSocket connection');
                    this.isConnecting = false;
                    reject(new Error('Authentication required for WebSocket connection'));
                    return;
                }

                // Use query parameter for WebSocket authentication (as backend expects)
                const wsUrl = `${wsProtocol}//${wsHost}/api/v3/socket/${processId}?user_id=${encodeURIComponent(userId)}`;

                console.log('Connecting to WebSocket:', wsUrl);
                
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    console.log('WebSocket connected successfully');
                    this.reconnectAttempts = 0;
                    this.isConnecting = false;
                    this.emit('connection_status', { connected: true });
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    try {
                        const message: StreamMessage = JSON.parse(event.data);
                        this.handleMessage(message);
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error, 'Raw data:', event.data);
                        this.emit('error', { error: 'Failed to parse WebSocket message' });
                    }
                };

                this.ws.onclose = (event) => {
                    console.log('WebSocket disconnected', event.code, event.reason);
                    this.isConnecting = false;
                    this.emit('connection_status', { connected: false });
                    
                    if (event.code !== 1000) {
                        this.attemptReconnect();
                    }
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.isConnecting = false;
                    this.emit('error', { error: 'WebSocket connection failed' });
                    reject(error);
                };

            } catch (error) {
                this.isConnecting = false;
                reject(error);
            }
        });
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect(): void {
        console.log('Manually disconnecting WebSocket');
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        this.reconnectAttempts = this.maxReconnectAttempts;
        
        if (this.ws) {
            this.ws.close(1000, 'Manual disconnect');
            this.ws = null;
        }
        this.planSubscriptions.clear();
        this.isConnecting = false;
    }

    /**
     * Subscribe to plan updates
     */
    subscribeToPlan(planId: string): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = {
                type: 'subscribe_plan',
                plan_id: planId
            };
            
            this.ws.send(JSON.stringify(message));
            this.planSubscriptions.add(planId);
            console.log(`Subscribed to plan updates: ${planId}`);
        }
    }

    /**
     * Unsubscribe from plan updates
     */
    unsubscribeFromPlan(planId: string): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = {
                type: 'unsubscribe_plan',
                plan_id: planId
            };
            
            this.ws.send(JSON.stringify(message));
            this.planSubscriptions.delete(planId);
            console.log(`Unsubscribed from plan updates: ${planId}`);
        }
    }

    /**
     * Add event listener
     */
    on(eventType: string, callback: (message: StreamMessage) => void): () => void {
        if (!this.listeners.has(eventType)) {
            this.listeners.set(eventType, new Set());
        }
        
        this.listeners.get(eventType)!.add(callback);

        return () => {
            const eventListeners = this.listeners.get(eventType);
            if (eventListeners) {
                eventListeners.delete(callback);
                if (eventListeners.size === 0) {
                    this.listeners.delete(eventType);
                }
            }
        };
    }

    /**
     * Remove event listener
     */
    off(eventType: string, callback: (message: StreamMessage) => void): void {
        const eventListeners = this.listeners.get(eventType);
        if (eventListeners) {
            eventListeners.delete(callback);
            if (eventListeners.size === 0) {
                this.listeners.delete(eventType);
            }
        }
    }

    /**
     * Emit event to listeners
     */
    private emit(eventType: string, data: any): void {
        const message: StreamMessage = {
            type: eventType as any,
            data,
            timestamp: new Date().toISOString()
        };

        const eventListeners = this.listeners.get(eventType);
        if (eventListeners) {
            eventListeners.forEach(callback => {
                try {
                    callback(message);
                } catch (error) {
                    console.error('Error in WebSocket event listener:', error);
                }
            });
        }
    }

    /**
     * Handle incoming WebSocket messages
     */
    private handleMessage(message: StreamMessage): void {
        console.log('WebSocket message received:', message);

        if (message.type) {
            this.emit(message.type, message.data);
        }

        if (message.type === 'plan_approval_request') {
            console.log('Plan approval request received via WebSocket:', message.data);
        }

        this.emit('message', message);
    }

    /**
     * Attempt to reconnect with exponential backoff
     */
    private attemptReconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached - stopping reconnect attempts');
            this.emit('error', { error: 'Max reconnection attempts reached' });
            return;
        }

        if (this.isConnecting || this.reconnectTimer) {
            console.log('Reconnection attempt already in progress');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Scheduling reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay/1000}s`);
        
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            console.log(`Attempting reconnection (attempt ${this.reconnectAttempts})`);
            
            this.connect()
                .then(() => {
                    console.log('Reconnection successful - re-subscribing to plans');
                    this.planSubscriptions.forEach(planId => {
                        this.subscribeToPlan(planId);
                    });
                })
                .catch((error) => {
                    console.error('Reconnection failed:', error);
                });
        }, delay);
    }

    /**
     * Get connection status
     */
    isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }

    /**
     * Send message to server
     */
    send(message: any): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket is not connected. Cannot send message:', message);
        }
    }

    /**
     * Send plan approval response
     */
    sendPlanApprovalResponse(response: PlanApprovalResponseData): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected - cannot send plan approval response');
            this.emit('error', { error: 'Cannot send plan approval response - WebSocket not connected' });
            return;
        }

        try {
            const message = {
                type: 'plan_approval_response',
                data: response
            };
            this.ws.send(JSON.stringify(message));
            console.log('Plan approval response sent:', response);
        } catch (error) {
            console.error('Failed to send plan approval response:', error);
            this.emit('error', { error: 'Failed to send plan approval response' });
        }
    }
}

export const webSocketService = new WebSocketService();
export default webSocketService;