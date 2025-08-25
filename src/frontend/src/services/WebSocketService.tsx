/**
 * WebSocket Service for real-time plan execution streaming
 */

export interface StreamMessage {
    type: 'plan_update' | 'step_update' | 'agent_message' | 'error' | 'connection_status';
    plan_id?: string;
    session_id?: string;
    data?: any;
    timestamp?: string;
}

export interface StreamingPlanUpdate {
    plan_id: string;
    session_id: string;
    step_id?: string;
    agent_name?: string;
    content?: string;
    status?: 'in_progress' | 'completed' | 'error';
    message_type?: 'thinking' | 'action' | 'result' | 'clarification_needed';
}

class WebSocketService {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;
    private listeners: Map<string, Set<(message: StreamMessage) => void>> = new Map();
    private planSubscriptions: Set<string> = new Set();

    /**
     * Get WebSocket URL with dynamic configuration
     */
    private getWebSocketUrl(path: string = '/ws/streaming'): string {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        
        // Priority: Environment variable > Current host > Localhost fallback
        let wsHost = '';
        
        if (process.env.REACT_APP_WS_HOST) {
            wsHost = process.env.REACT_APP_WS_HOST;
        } else if (process.env.REACT_APP_API_BASE_URL) {
            // Extract host from API base URL
            try {
                const url = new URL(process.env.REACT_APP_API_BASE_URL);
                wsHost = url.host;
            } catch {
                wsHost = window.location.host || '127.0.0.1:8000';
            }
        } else {
            wsHost = window.location.host || '127.0.0.1:8000';
        }
        
        return `${wsProtocol}//${wsHost}${path}`;
    }

    /**
     * Create a standalone WebSocket connection for plan approval
     */
    createApprovalWebSocket(planId: string): Promise<WebSocket> {
        return new Promise((resolve, reject) => {
            try {
                const wsUrl = this.getWebSocketUrl(`/api/v3/ws/${planId}`);
                console.log('Creating approval WebSocket:', wsUrl);
                
                const ws = new WebSocket(wsUrl);
                
                ws.onopen = () => {
                    console.log('Approval WebSocket connected for plan:', planId);
                    resolve(ws);
                };
                
                ws.onerror = (error) => {
                    console.error('Approval WebSocket error:', error);
                    reject(error);
                };
                
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * Connect to WebSocket server
     */
    connect(customPath?: string): Promise<void> {
        return new Promise((resolve, reject) => {
            try {
                // Get WebSocket URL from environment or default
                const wsUrl = this.getWebSocketUrl(customPath || '/ws/streaming');

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
                        const message: StreamMessage = JSON.parse(event.data);
                        this.handleMessage(message);
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error);
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
    private handleMessage(message: StreamMessage): void {
        console.log('WebSocket message received:', message);

        // Emit to specific event listeners
        if (message.type) {
            this.emit(message.type, message.data);
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
     * Get current WebSocket URL configuration
     */
    getCurrentWebSocketUrl(): string {
        return this.getWebSocketUrl('/ws/streaming');
    }

    /**
     * Get approval WebSocket URL for a specific plan
     */
    getApprovalWebSocketUrl(planId: string): string {
        return this.getWebSocketUrl(`/api/v3/ws/${planId}`);
    }
}

// Export singleton instance
export const webSocketService = new WebSocketService();
export default webSocketService;