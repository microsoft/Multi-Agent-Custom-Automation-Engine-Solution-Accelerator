import { getUserId } from '../api/config';

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

// Add these new interfaces after StreamingPlanUpdate
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
    private processId: string | null = null; // Add this to store the process ID
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;
    private listeners: Map<string, Set<(message: StreamMessage) => void>> = new Map();
    private planSubscriptions: Set<string> = new Set();

    /**
     * Connect to WebSocket server
     */
    connect(): Promise<void> {
        // If already connected, return resolved promise
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return Promise.resolve();
        }

        // If already connecting, wait for that connection
        if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
            console.log('WebSocket connection already in progress');
            return new Promise((resolve, reject) => {
                const checkConnection = () => {
                    if (this.ws?.readyState === WebSocket.OPEN) {
                        resolve();
                    } else if (this.ws?.readyState === WebSocket.CLOSED) {
                        reject(new Error('Connection failed'));
                    } else {
                        setTimeout(checkConnection, 100);
                    }
                };
                checkConnection();
            });
        }
        return new Promise((resolve, reject) => {
            try {
                // Get WebSocket URL from environment or default to localhost
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsHost = process.env.REACT_APP_WS_HOST || '127.0.0.1:8000';
                const processId = crypto.randomUUID(); // Generate unique process ID for this session

                // const wsUrl = `${wsProtocol}//${wsHost}/api/v3/socket/${processId}`;
                // Build WebSocket URL with authentication headers as query parameters
            const userId = getUserId(); // Import this from config
            const wsUrl = `${wsProtocol}//${wsHost}/api/v3/socket/${processId}?user_id=${encodeURIComponent(userId)}`;

                console.log('Connecting to WebSocket:', wsUrl);
                
                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.reconnectAttempts = 0;
                    this.emit('connection_status', { connected: true });
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    try {
                        const message: StreamMessage =  JSON.parse(event.data);
                        this.handleMessage(message);
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error, 'Raw data:', event.data);
                        this.emit('error', { error: 'Failed to parse WebSocket message' });
                    }
                };

                this.ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    this.emit('connection_status', { connected: false });
                    this.attemptReconnect();
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.emit('error', { error: 'WebSocket connection failed' });
                    reject(error);
                };

            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.planSubscriptions.clear();
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

        // Return unsubscribe function
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
    /**
 * Handle incoming WebSocket messages
 */
    private handleMessage(message: StreamMessage): void {
        console.log('WebSocket message received:', message);

        // Emit to specific event listeners
        if (message.type) {
            this.emit(message.type, message.data);
        }

        // Handle plan approval requests specifically
        if (message.type === 'plan_approval_request') {
            console.log('Plan approval request received via WebSocket:', message.data);
        }

        // Emit to general message listeners
        this.emit('message', message);
    }

    /**
     * Attempt to reconnect with exponential backoff
     */
    private attemptReconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached');
            this.emit('error', { error: 'Max reconnection attempts reached' });
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            this.connect()
                .then(() => {
                    // Re-subscribe to all plans
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

// Export singleton instance
export const webSocketService = new WebSocketService();
export default webSocketService;