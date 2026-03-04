import { getApiUrl, getUserId } from '../api/config';
import { PlanDataService } from './PlanDataService';
import { ParsedPlanApprovalRequest, StreamingPlanUpdate, StreamMessage, WebsocketMessageType } from '../models';


class WebSocketService {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000; // 1s base, exponential: 1s, 2s, 4s, 8s, 16s
    private listeners: Map<string, Set<(message: StreamMessage) => void>> = new Map();
    private planSubscriptions: Set<string> = new Set();
    private reconnectTimer: NodeJS.Timeout | null = null;
    private isConnecting = false;
    private intentionalDisconnect = false;
    private lastPlanId: string | undefined;
    private lastProcessId: string | undefined;


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
        const socketPath = hasApiSegment ? '/v4/socket' : '/api/v4/socket';
        const url = `${base}${socketPath}${processId ? `/${processId}` : `/${planId}`}?user_id=${userId || ''}`;
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
                this.intentionalDisconnect = false;
                this.lastPlanId = planId;
                this.lastProcessId = processId;
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
                    /* P1: Only auto-reconnect if not intentional and not a clean close */
                    if (!this.intentionalDisconnect && event.code !== 1000 &&
                        this.reconnectAttempts < this.maxReconnectAttempts) {
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
        this.intentionalDisconnect = true;
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        this.reconnectAttempts = this.maxReconnectAttempts;
        if (this.ws) {
            const socket = this.ws;
            this.ws = null;

            // Detach handlers so no stale callbacks fire during/after close
            socket.onopen = null;
            socket.onmessage = null;
            socket.onerror = null;
            socket.onclose = null;

            if (socket.readyState === WebSocket.OPEN) {
                // Normal close
                socket.close(1000, 'Manual disconnect');
            } else if (socket.readyState === WebSocket.CONNECTING) {
                // Still handshaking — wait for open then close cleanly.
                // This avoids the "WebSocket closed before connection established" warning.
                socket.addEventListener('open', () => socket.close(1000, 'Manual disconnect'), { once: true });
                socket.addEventListener('error', () => { /* handshake failed — nothing to close */ }, { once: true });
            }
            // CLOSING / CLOSED — no action needed
        }
        this.planSubscriptions.clear();
        this.isConnecting = false;
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

    onErrorMessage(callback: (data: any) => void): () => void {
        return this.on(WebsocketMessageType.ERROR_MESSAGE, (message: StreamMessage) => {
            callback(message.data);
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
                if (message.data) {
                    const transformed = PlanDataService.parseAgentMessage(message);
                    this.emit(WebsocketMessageType.AGENT_MESSAGE, transformed);

                }
                break;
            }

            case WebsocketMessageType.AGENT_MESSAGE_STREAMING: {
                if (message.data) {
                    const streamedMessage = PlanDataService.parseAgentMessageStreaming(message);
                    this.emit(WebsocketMessageType.AGENT_MESSAGE_STREAMING, streamedMessage);
                }
                break;
            }

            case WebsocketMessageType.USER_CLARIFICATION_REQUEST: {
                if (message.data) {
                    const transformed = PlanDataService.parseUserClarificationRequest(message);
                    this.emit(WebsocketMessageType.USER_CLARIFICATION_REQUEST, transformed);
                }
                break;
            }


            case WebsocketMessageType.AGENT_TOOL_MESSAGE: {
                if (message.data) {
                    //const transformed = PlanDataService.parseUserClarificationRequest(message);
                    this.emit(WebsocketMessageType.AGENT_TOOL_MESSAGE, message);
                }
                break;
            }
            case WebsocketMessageType.FINAL_RESULT_MESSAGE: {
                if (message.data) {
                    const transformed = PlanDataService.parseFinalResultMessage(message);
                    this.emit(WebsocketMessageType.FINAL_RESULT_MESSAGE, transformed);
                }
                break;
            }
            case WebsocketMessageType.ERROR_MESSAGE: {
            this.emit(WebsocketMessageType.ERROR_MESSAGE, message.data); // Emit the data
            break;
            }
            case WebsocketMessageType.USER_CLARIFICATION_RESPONSE:
            case WebsocketMessageType.REPLAN_APPROVAL_REQUEST:
            case WebsocketMessageType.REPLAN_APPROVAL_RESPONSE:
            case WebsocketMessageType.PLAN_APPROVAL_RESPONSE:
            case WebsocketMessageType.AGENT_STREAM_START:
            case WebsocketMessageType.AGENT_STREAM_END:
            case WebsocketMessageType.SYSTEM_MESSAGE: {
                this.emit(message.type, message);
                break;
            }

            default: {
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
        /* P1: exponential backoff — 1s, 2s, 4s, 8s, 16s (capped) */
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
            16000,
        );
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            if (this.intentionalDisconnect) return;
            if (this.lastPlanId) {
                this.connect(this.lastPlanId, this.lastProcessId).catch(() => {
                    /* If reconnect fails, onclose will trigger another attempt */
                });
            } else {
                this.emit('error', { error: 'Connection lost — no planId available for reconnection' });
            }
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
            const v4Response = {
                m_plan_id: response.plan_id,
                approved: response.approved,
                feedback: response.feedback || response.user_response || response.human_clarification || '',
            };
            const message = {
                type: WebsocketMessageType.PLAN_APPROVAL_RESPONSE,
                data: v4Response
            };
            this.ws.send(JSON.stringify(message));
        } catch {
            this.emit('error', { error: 'Failed to send plan approval response' });
        }
    }
}

export const webSocketService = new WebSocketService();
export default webSocketService;