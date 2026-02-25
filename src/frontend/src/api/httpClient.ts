/**
 * Centralized HTTP Client with Interceptors
 * 
 * A singleton HTTP client that provides:
 * - Request interceptors for automatic auth header attachment
 * - Response interceptors for uniform error handling
 * - Built-in params serialization
 * - Configurable timeout
 * - Configurable base URL
 * 
 * Usage:
 * ```typescript
 * import { httpClient } from './httpClient';
 * 
 * // GET request
 * const data = await httpClient.get('/api/users', { params: { page: 1 } });
 * 
 * // POST request
 * const result = await httpClient.post('/api/users', { name: 'John' });
 * ```
 */

import { getApiUrl, getUserId } from './config';

// Types
export interface HttpClientConfig {
    baseURL?: string;
    timeout?: number;
    headers?: Record<string, string>;
}

export interface RequestConfig {
    params?: Record<string, any>;
    headers?: Record<string, string>;
    timeout?: number;
    skipAuth?: boolean;
}

export interface HttpResponse<T = any> {
    data: T;
    status: number;
    statusText: string;
    headers: Headers;
}

export interface HttpError extends Error {
    status?: number;
    statusText?: string;
    data?: any;
    isTimeout?: boolean;
    isNetworkError?: boolean;
}

export interface InterceptorRequestConfig {
    url: string;
    method: string;
    headers: Record<string, string>;
    body?: any;
}

type RequestInterceptor = (config: InterceptorRequestConfig) => InterceptorRequestConfig | Promise<InterceptorRequestConfig>;

type ResponseInterceptor = (response: HttpResponse) => HttpResponse | Promise<HttpResponse>;

type ErrorInterceptor = (error: HttpError) => HttpError | Promise<HttpError>;

/**
 * HTTP Client class with interceptor support
 */
export class HttpClient {
    private baseURL: string = '';
    private defaultTimeout: number = 30000; // 30 seconds default
    private defaultHeaders: Record<string, string> = {};
    private requestInterceptors: RequestInterceptor[] = [];
    private responseInterceptors: ResponseInterceptor[] = [];
    private errorInterceptors: ErrorInterceptor[] = [];

    constructor(config?: HttpClientConfig) {
        if (config?.baseURL) {
            this.baseURL = config.baseURL;
        }
        if (config?.timeout) {
            this.defaultTimeout = config.timeout;
        }
        if (config?.headers) {
            this.defaultHeaders = { ...config.headers };
        }

        // Add default request interceptor for auth headers
        this.addRequestInterceptor(this.authInterceptor.bind(this));
        
        // Add default response interceptor for error normalization
        this.addErrorInterceptor(this.defaultErrorInterceptor.bind(this));
    }

    /**
     * Set the base URL for all requests
     */
    setBaseURL(url: string): void {
        this.baseURL = url;
    }

    /**
     * Get the current base URL (with fallback to config)
     */
    getBaseURL(): string {
        if (this.baseURL) {
            return this.baseURL;
        }
        return getApiUrl() || '';
    }

    /**
     * Set default timeout for all requests
     */
    setTimeout(timeout: number): void {
        this.defaultTimeout = timeout;
    }

    /**
     * Set default headers for all requests
     */
    setDefaultHeaders(headers: Record<string, string>): void {
        this.defaultHeaders = { ...this.defaultHeaders, ...headers };
    }

    /**
     * Add a request interceptor
     * @param interceptor Function to transform request config
     * @returns Function to remove the interceptor
     */
    addRequestInterceptor(interceptor: RequestInterceptor): () => void {
        this.requestInterceptors.push(interceptor);
        return () => {
            const index = this.requestInterceptors.indexOf(interceptor);
            if (index > -1) {
                this.requestInterceptors.splice(index, 1);
            }
        };
    }

    /**
     * Add a response interceptor
     * @param interceptor Function to transform response
     * @returns Function to remove the interceptor
     */
    addResponseInterceptor(interceptor: ResponseInterceptor): () => void {
        this.responseInterceptors.push(interceptor);
        return () => {
            const index = this.responseInterceptors.indexOf(interceptor);
            if (index > -1) {
                this.responseInterceptors.splice(index, 1);
            }
        };
    }

    /**
     * Add an error interceptor
     * @param interceptor Function to handle/transform errors
     * @returns Function to remove the interceptor
     */
    addErrorInterceptor(interceptor: ErrorInterceptor): () => void {
        this.errorInterceptors.push(interceptor);
        return () => {
            const index = this.errorInterceptors.indexOf(interceptor);
            if (index > -1) {
                this.errorInterceptors.splice(index, 1);
            }
        };
    }

    /**
     * Default auth interceptor - adds authentication headers
     */
    private authInterceptor(config: InterceptorRequestConfig): InterceptorRequestConfig {
        const userId = getUserId();
        const token = localStorage.getItem('token');

        // Add user ID header
        if (userId) {
            config.headers['x-ms-client-principal-id'] = userId;
        }

        // Add Bearer token if available
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }

        return config;
    }

    /**
     * Default error interceptor - normalizes error format
     */
    private defaultErrorInterceptor(error: HttpError): HttpError {
        // Log errors in development
        if (process.env.NODE_ENV !== 'production') {
            console.error('[HttpClient Error]', {
                message: error.message,
                status: error.status,
                data: error.data,
            });
        }

        return error;
    }

    /**
     * Build URL with query parameters
     */
    private buildUrl(endpoint: string, params?: Record<string, any>): string {
        const baseURL = this.getBaseURL();
        let url = endpoint.startsWith('http') ? endpoint : `${baseURL}${endpoint}`;

        if (params && Object.keys(params).length > 0) {
            const searchParams = new URLSearchParams();
            Object.entries(params).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    if (Array.isArray(value)) {
                        value.forEach(v => searchParams.append(key, String(v)));
                    } else if (typeof value === 'object') {
                        searchParams.append(key, JSON.stringify(value));
                    } else {
                        searchParams.append(key, String(value));
                    }
                }
            });
            const queryString = searchParams.toString();
            if (queryString) {
                url += (url.includes('?') ? '&' : '?') + queryString;
            }
        }

        return url;
    }

    /**
     * Create an HTTP error object
     */
    private createHttpError(message: string, options?: Partial<HttpError>): HttpError {
        const error = new Error(message) as HttpError;
        error.name = 'HttpError';
        if (options) {
            Object.assign(error, options);
        }
        return error;
    }

    /**
     * Execute the request with interceptors
     */
    private async request<T>(
        method: string,
        endpoint: string,
        data?: any,
        config?: RequestConfig
    ): Promise<T> {
        const url = this.buildUrl(endpoint, config?.params);
        const timeout = config?.timeout ?? this.defaultTimeout;

        // Prepare headers
        let headers: Record<string, string> = {
            ...this.defaultHeaders,
            ...(config?.headers || {}),
        };

        // Set Content-Type for non-FormData
        if (data && !(data instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        // Build request config
        let requestConfig: InterceptorRequestConfig = {
            url,
            method,
            headers,
            body: data,
        };

        // Apply request interceptors (unless skipAuth is true)
        if (!config?.skipAuth) {
            for (const interceptor of this.requestInterceptors) {
                requestConfig = await interceptor(requestConfig);
            }
        }

        // Prepare fetch options
        const fetchOptions: RequestInit = {
            method: requestConfig.method,
            headers: requestConfig.headers,
        };

        // Handle body
        if (requestConfig.body !== undefined) {
            if (requestConfig.body instanceof FormData) {
                fetchOptions.body = requestConfig.body;
                // Remove Content-Type to let browser set it with boundary
                delete (fetchOptions.headers as Record<string, string>)['Content-Type'];
            } else {
                fetchOptions.body = JSON.stringify(requestConfig.body);
            }
        }

        // Create abort controller for timeout
        const controller = new AbortController();
        fetchOptions.signal = controller.signal;

        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(requestConfig.url, fetchOptions);
            clearTimeout(timeoutId);

            // Parse response
            const contentType = response.headers.get('content-type');
            const isJson = contentType?.includes('application/json');
            const responseData = isJson ? await response.json() : await response.text();

            // Handle non-OK responses
            if (!response.ok) {
                let error = this.createHttpError(
                    responseData?.message || responseData || response.statusText || 'Request failed',
                    {
                        status: response.status,
                        statusText: response.statusText,
                        data: responseData,
                    }
                );

                // Apply error interceptors
                for (const interceptor of this.errorInterceptors) {
                    error = await interceptor(error);
                }

                throw error;
            }

            // Create response object
            let httpResponse: HttpResponse<T> = {
                data: responseData,
                status: response.status,
                statusText: response.statusText,
                headers: response.headers,
            };

            // Apply response interceptors
            for (const interceptor of this.responseInterceptors) {
                httpResponse = await interceptor(httpResponse);
            }

            return httpResponse.data;
        } catch (err: any) {
            clearTimeout(timeoutId);

            // Handle abort/timeout
            if (err.name === 'AbortError') {
                let error = this.createHttpError(`Request timeout after ${timeout}ms`, {
                    isTimeout: true,
                });

                for (const interceptor of this.errorInterceptors) {
                    error = await interceptor(error);
                }

                throw error;
            }

            // Handle network errors
            if (err instanceof TypeError && err.message === 'Failed to fetch') {
                let error = this.createHttpError('Network error - please check your connection', {
                    isNetworkError: true,
                });

                for (const interceptor of this.errorInterceptors) {
                    error = await interceptor(error);
                }

                throw error;
            }

            // Re-throw HttpErrors as-is
            if (err.name === 'HttpError') {
                throw err;
            }

            // Wrap unknown errors
            let error = this.createHttpError(err.message || 'Unknown error occurred');
            for (const interceptor of this.errorInterceptors) {
                error = await interceptor(error);
            }
            throw error;
        }
    }

    /**
     * GET request
     */
    async get<T = any>(endpoint: string, config?: RequestConfig): Promise<T> {
        return this.request<T>('GET', endpoint, undefined, config);
    }

    /**
     * POST request
     */
    async post<T = any>(endpoint: string, data?: any, config?: RequestConfig): Promise<T> {
        return this.request<T>('POST', endpoint, data, config);
    }

    /**
     * PUT request
     */
    async put<T = any>(endpoint: string, data?: any, config?: RequestConfig): Promise<T> {
        return this.request<T>('PUT', endpoint, data, config);
    }

    /**
     * PATCH request
     */
    async patch<T = any>(endpoint: string, data?: any, config?: RequestConfig): Promise<T> {
        return this.request<T>('PATCH', endpoint, data, config);
    }

    /**
     * DELETE request
     */
    async delete<T = any>(endpoint: string, config?: RequestConfig): Promise<T> {
        return this.request<T>('DELETE', endpoint, undefined, config);
    }

    /**
     * Upload file(s) using FormData
     */
    async upload<T = any>(endpoint: string, formData: FormData, config?: RequestConfig): Promise<T> {
        return this.request<T>('POST', endpoint, formData, config);
    }

    /**
     * Make a request without authentication headers
     */
    async requestWithoutAuth<T = any>(
        method: string,
        endpoint: string,
        data?: any,
        config?: RequestConfig
    ): Promise<T> {
        return this.request<T>(method, endpoint, data, { ...config, skipAuth: true });
    }
}

/**
 * Singleton HTTP client instance
 * Pre-configured with auth interceptors and sensible defaults
 */
export const httpClient = new HttpClient({
    timeout: 30000, // 30 second default timeout
});

// Export default instance
export default httpClient;
