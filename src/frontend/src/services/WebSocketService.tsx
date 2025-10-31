import { getApiUrl, getUserId, headerBuilder } from '../api/config';
import { PlanDataService } from './PlanDataService';
import { MPlanData, ParsedPlanApprovalRequest, StreamingPlanUpdate, StreamMessage, WebsocketMessageType } from '../models';


class WebSocketService {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 12000;
    private listeners: Map<string, Set<(message: StreamMessage) => void>> = new Map();
    private planSubscriptions: Set<string> = new Set();
    private reconnectTimer: NodeJS.Timeout | null = null;
    private isConnecting = false;


    private buildSocketUrl(processId?: string, planId?: string): string {
        const baseWsUrl = getApiUrl() || 'ws://localhost:8000';
        // Trim and remove trailing slashes
        let base = (baseWsUrl || '').trim().replace(/\/+$/, '');
        // Normalize protocol: http -> ws, https -> wss
        base = base.replace(/^http:\/\//i, 'ws://')
            .replace(/^https:\/\//i, 'wss://');

        // Leave ws/wss as-is; anything else is assumed already correct

        // Decide path addition
        let userId = getUserId();
        const hasApiSegment = /\/api(\/|$)/i.test(base);
        const socketPath = hasApiSegment ? '/v3/socket' : '/api/v3/socket';
        const url = `${base}${socketPath}${processId ? `/${processId}` : `/${planId}`}?user_id=${userId || ''}`;
        console.log("Constructed WebSocket URL:", url);
        return url;
    }
    connect(planId: string, processId?: string): Promise<void> {
        return new Promise((resolve, reject) => {
            if (this.isConnecting) {
                reject(new Error('Connection already in progress'));
                return;
            }
            if (this.ws?.readyState === WebSocket.OPEN) {
                resolve();
                return;
            }
            try {
                this.isConnecting = true;
                const wsUrl = this.buildSocketUrl(processId, planId);
                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    this.isConnecting = false;
                    this.reconnectAttempts = 0;
                    if (this.reconnectTimer) {
                        clearTimeout(this.reconnectTimer);
                        this.reconnectTimer = null;
                    }
                    this.emit('connection_status', { connected: true });
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        this.handleMessage(message);
                    } catch (error) {
                        console.error('Failed to parse WebSocket message:', error);
                    }
                };

                this.ws.onclose = (event) => {
                    this.isConnecting = false;
                    this.ws = null;
                    this.emit('connection_status', { connected: false });
                    if (this.reconnectAttempts < this.maxReconnectAttempts && event.code !== 1000) {
                        this.attemptReconnect();
                    }
                };

                this.ws.onerror = () => {
                    this.isConnecting = false;
                    if (this.reconnectAttempts === 0) {
                        reject(new Error('WebSocket connection failed'));
                    }
                    this.emit('error', { error: 'WebSocket connection error' });
                };
            } catch (error) {
                this.isConnecting = false;
                reject(error);
            }
        });
    }

    disconnect(): void {
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

    subscribeToPlan(planId: string): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = { type: 'subscribe_plan', plan_id: planId };
            this.ws.send(JSON.stringify(message));
            this.planSubscriptions.add(planId);
        }
    }

    unsubscribeFromPlan(planId: string): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = { type: 'unsubscribe_plan', plan_id: planId };
            this.ws.send(JSON.stringify(message));
            this.planSubscriptions.delete(planId);
        }
    }

    on(eventType: string, callback: (message: StreamMessage) => void): () => void {
        if (!this.listeners.has(eventType)) {
            this.listeners.set(eventType, new Set());
        }
        this.listeners.get(eventType)!.add(callback);
        return () => {
            const setRef = this.listeners.get(eventType);
            if (setRef) {
                setRef.delete(callback);
                if (setRef.size === 0) this.listeners.delete(eventType);
            }
        };
    }

    off(eventType: string, callback: (message: StreamMessage) => void): void {
        const setRef = this.listeners.get(eventType);
        if (setRef) {
            setRef.delete(callback);
            if (setRef.size === 0) this.listeners.delete(eventType);
        }
    }

    onConnectionChange(callback: (connected: boolean) => void): () => void {
        return this.on('connection_status', (message: StreamMessage) => {
            callback(message.data?.connected || false);
        });
    }

    onStreamingMessage(callback: (message: StreamingPlanUpdate) => void): () => void {
        return this.on(WebsocketMessageType.AGENT_MESSAGE, (message: StreamMessage) => {
            if (message.data) callback(message.data);
        });
    }

    onPlanApprovalRequest(callback: (approvalRequest: ParsedPlanApprovalRequest) => void): () => void {
        return this.on(WebsocketMessageType.PLAN_APPROVAL_REQUEST, (message: StreamMessage) => {
            if (message.data) callback(message.data);
        });
    }

    onPlanApprovalResponse(callback: (response: any) => void): () => void {
        return this.on(WebsocketMessageType.PLAN_APPROVAL_RESPONSE, (message: StreamMessage) => {
            if (message.data) callback(message.data);
        });
    }

    private emit(eventType: string, data: any): void {
        const message: StreamMessage = {
            type: eventType as any,
            data,
            timestamp: new Date().toISOString()
        };
        const setRef = this.listeners.get(eventType);
        if (setRef) {
            setRef.forEach(cb => {
                try { cb(message); } catch (e) { console.error('Listener error:', e); }
            });
        }
    }

    private handleMessage(message: StreamMessage): void {

        switch (message.type) {
            case WebsocketMessageType.PLAN_APPROVAL_REQUEST: {
                console.log("Message Plan Approval Request':", message);
                const parsedData = PlanDataService.parsePlanApprovalRequest(message.data);
                if (parsedData) {
                    const structuredMessage: ParsedPlanApprovalRequest = {
                        type: WebsocketMessageType.PLAN_APPROVAL_REQUEST,
                        plan_id: parsedData.id,
                        parsedData,
                        rawData: message.data
                    };
                    this.emit(WebsocketMessageType.PLAN_APPROVAL_REQUEST, structuredMessage);
                } else {
                    this.emit('error', { error: 'Failed to parse plan approval request' });
                }
                break;
            }

            case WebsocketMessageType.AGENT_MESSAGE: {
                console.log("Message Agent':", message);
                if (message.data) {
                    console.log('WebSocket message received:', message);
                    const transformed = PlanDataService.parseAgentMessage(message);
                    console.log('Transformed AGENT_MESSAGE:', transformed);
                    this.emit(WebsocketMessageType.AGENT_MESSAGE, transformed);

                }
                break;
            }

            case WebsocketMessageType.AGENT_MESSAGE_STREAMING: {
                console.log("Message streamming agent buffer:", message);
                if (message.data) {
                    const streamedMessage = PlanDataService.parseAgentMessageStreaming(message);
                    console.log('WebSocket AGENT_MESSAGE_STREAMING message received:', streamedMessage);
                    this.emit(WebsocketMessageType.AGENT_MESSAGE_STREAMING, streamedMessage);
                }
                break;
            }

            case WebsocketMessageType.USER_CLARIFICATION_REQUEST: {
                console.log("Message clarification':", message);
                if (message.data) {
                    const transformed = PlanDataService.parseUserClarificationRequest(message);
                    console.log('WebSocket USER_CLARIFICATION_REQUEST message received:', transformed);
                    this.emit(WebsocketMessageType.USER_CLARIFICATION_REQUEST, transformed);
                }
                break;
            }


            case WebsocketMessageType.AGENT_TOOL_MESSAGE: {
                console.log("Message agent tool':", message);
                if (message.data) {
                    //const transformed = PlanDataService.parseUserClarificationRequest(message);
                    this.emit(WebsocketMessageType.AGENT_TOOL_MESSAGE, message);
                }
                break;
            }
            case WebsocketMessageType.FINAL_RESULT_MESSAGE: {
                console.log("Message final result':", message);
                if (message.data) {
                    const transformed = PlanDataService.parseFinalResultMessage(message);
                    console.log('WebSocket FINAL_RESULT_MESSAGE received:', transformed);
                    this.emit(WebsocketMessageType.FINAL_RESULT_MESSAGE, transformed);
                }
                break;
            }
            case WebsocketMessageType.USER_CLARIFICATION_RESPONSE:
            case WebsocketMessageType.REPLAN_APPROVAL_REQUEST:
            case WebsocketMessageType.REPLAN_APPROVAL_RESPONSE:
            case WebsocketMessageType.PLAN_APPROVAL_RESPONSE:
            case WebsocketMessageType.AGENT_STREAM_START:
            case WebsocketMessageType.AGENT_STREAM_END:
            case WebsocketMessageType.SYSTEM_MESSAGE: {
                console.log("Message other types':", message);
                this.emit(message.type, message);
                break;
            }

            default: {
                console.log("Message default':", message);
                this.emit(message.type, message);
                break;
            }
        }
    }

    private attemptReconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.emit('error', { error: 'Max reconnection attempts reached' });
            return;
        }
        if (this.isConnecting || this.reconnectTimer) return;
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.emit('error', { error: 'Connection lost - manual reconnection required' });
        }, delay);
    }

    isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }

    send(message: any): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected. Cannot send:', message);
        }
    }

    sendPlanApprovalResponse(response: {
        plan_id: string;
        session_id: string;
        approved: boolean;
        feedback?: string;
        user_response?: string;
        human_clarification?: string;
    }): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.emit('error', { error: 'Cannot send plan approval response - WebSocket not connected' });
            return;
        }
        try {
            const v3Response = {
                m_plan_id: response.plan_id,
                approved: response.approved,
                feedback: response.feedback || response.user_response || response.human_clarification || '',
            };
            const message = {
                type: WebsocketMessageType.PLAN_APPROVAL_RESPONSE,
                data: v3Response
            };
            this.ws.send(JSON.stringify(message));
        } catch {
            this.emit('error', { error: 'Failed to send plan approval response' });
        }
    }
}

export const webSocketService = new WebSocketService();
export default webSocketService;