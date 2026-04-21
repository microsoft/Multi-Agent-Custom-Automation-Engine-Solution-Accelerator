/**
 * Centralized HTTP Client with Interceptors
 * 
 * Singleton class that wraps all API calls with:
 * - Automatic auth header injection via request interceptors
 * - Uniform error handling via response interceptors
 * - Built-in timeout, configurable base URL, and params serialization
 * 
 * Eliminates duplicated localStorage/header logic across API functions.
 */
import { getUserId } from './config';

type RequestConfig = RequestInit & { url: string };
type RequestInterceptor = (config: RequestConfig) => RequestConfig;
type ResponseInterceptor = (response: Response) => Response | Promise<Response>;

class HttpClient {
    private baseUrl: string;
    private requestInterceptors: RequestInterceptor[] = [];
    private responseInterceptors: ResponseInterceptor[] = [];
    private timeout: number;

    constructor(baseUrl = '', timeout = 30000) {
        this.baseUrl = baseUrl;
        this.timeout = timeout;
    }

    /** Set or update the base URL at runtime (after config is loaded) */
    setBaseUrl(url: string): void {
        this.baseUrl = url;
    }

    getBaseUrl(): string {
        return this.baseUrl;
    }

    /** Register a request interceptor (runs before every request) */
    addRequestInterceptor(interceptor: RequestInterceptor): void {
        this.requestInterceptors.push(interceptor);
    }

    /** Register a response interceptor (runs after every response) */
    addResponseInterceptor(interceptor: ResponseInterceptor): void {
        this.responseInterceptors.push(interceptor);
    }

    /** Build URL with query parameters */
    private buildUrl(path: string, params?: Record<string, unknown>): string {
        const base = this.baseUrl ? `${this.baseUrl}${path}` : path;
        if (!params) return base;

        const searchParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                searchParams.append(key, String(value));
            }
        });

        const queryString = searchParams.toString();
        return queryString ? `${base}?${queryString}` : base;
    }

    /** Core request method — applies interceptors, timeout, and error handling */
    private async request(
        path: string,
        options: RequestInit & { params?: Record<string, unknown> } = {}
    ): Promise<Response> {
        const { params, ...fetchOptions } = options;
        const url = this.buildUrl(path, params);

        // Build initial config
        let config: RequestConfig = { url, ...fetchOptions };

        // Run request interceptors
        for (const interceptor of this.requestInterceptors) {
            config = interceptor(config);
        }

        const { url: finalUrl, ...rest } = config;

        // Timeout via AbortController
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            let response = await fetch(finalUrl, {
                ...rest,
                signal: controller.signal,
            });

            // Run response interceptors
            for (const interceptor of this.responseInterceptors) {
                response = await interceptor(response);
            }

            return response;
        } finally {
            clearTimeout(timeoutId);
        }
    }

    /** HTTP GET */
    async get<T = unknown>(
        path: string,
        config?: { params?: Record<string, unknown>; headers?: Record<string, string> }
    ): Promise<T> {
        const response = await this.request(path, {
            method: 'GET',
            params: config?.params,
            headers: config?.headers,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Request failed');
        }

        const isJson = response.headers.get('content-type')?.includes('application/json');
        return isJson ? response.json() : (null as T);
    }

    /** HTTP POST */
    async post<T = unknown>(
        path: string,
        body?: unknown,
        config?: { headers?: Record<string, string> }
    ): Promise<T> {
        const response = await this.request(path, {
            method: 'POST',
            body: JSON.stringify(body),
            headers: {
                'Content-Type': 'application/json',
                ...config?.headers,
            },
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Request failed');
        }

        const isJson = response.headers.get('content-type')?.includes('application/json');
        return isJson ? response.json() : (null as T);
    }

    /** HTTP PUT */
    async put<T = unknown>(
        path: string,
        body?: unknown,
        config?: { headers?: Record<string, string> }
    ): Promise<T> {
        const response = await this.request(path, {
            method: 'PUT',
            body: JSON.stringify(body),
            headers: {
                'Content-Type': 'application/json',
                ...config?.headers,
            },
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Request failed');
        }

        const isJson = response.headers.get('content-type')?.includes('application/json');
        return isJson ? response.json() : (null as T);
    }

    /** HTTP DELETE */
    async del<T = unknown>(path: string): Promise<T> {
        const response = await this.request(path, { method: 'DELETE' });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Request failed');
        }

        const isJson = response.headers.get('content-type')?.includes('application/json');
        return isJson ? response.json() : (null as T);
    }

    /** Upload a FormData payload (multipart/form-data) */
    async upload<T = unknown>(path: string, formData: FormData): Promise<T> {
        // Don't set Content-Type — browser sets multipart boundary automatically
        const response = await this.request(path, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Upload failed');
        }

        const isJson = response.headers.get('content-type')?.includes('application/json');
        return isJson ? response.json() : (null as T);
    }

    /** HTTP POST without auth (used for login) */
    async postWithoutAuth<T = unknown>(path: string, body?: unknown): Promise<T> {
        const url = this.baseUrl ? `${this.baseUrl}${path}` : path;

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: body ? JSON.stringify(body) : undefined,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Request failed');
        }

        const isJson = response.headers.get('content-type')?.includes('application/json');
        return isJson ? response.json() : (null as T);
    }
}

// ──────────────────────────────────────────────
// Singleton instance with interceptors
// ──────────────────────────────────────────────

const httpClient = new HttpClient();

/**
 * Auth interceptor — single source of truth for userId header.
 * Eliminates repeated localStorage.getItem("userId") and manual headerBuilder() calls.
 */
httpClient.addRequestInterceptor((config) => {
    const userId = getUserId();
    const token = localStorage.getItem('token');

    const headers = new Headers(config.headers as HeadersInit);

    if (userId) {
        headers.set('x-ms-client-principal-id', String(userId));
    }
    if (token) {
        headers.set('Authorization', `Bearer ${token}`);
    }

    return { ...config, headers };
});

export default httpClient;
