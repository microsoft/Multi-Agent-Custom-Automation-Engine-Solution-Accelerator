/**
 * API Client - Backward-compatible wrapper around HttpClient
 * 
 * This module re-exports the httpClient methods in the original apiClient interface
 * for backward compatibility with existing code.
 * 
 * For new code, prefer importing directly from httpClient:
 * ```typescript
 * import { httpClient } from './httpClient';
 * ```
 */

import { httpClient, RequestConfig } from './httpClient';

/**
 * Legacy API client interface
 * Maps to the new HttpClient methods while maintaining the same API
 */
export const apiClient = {
    /**
     * GET request with optional query params
     */
    get: <T = any>(url: string, config?: { params?: Record<string, any> }): Promise<T> => {
        return httpClient.get<T>(url, config as RequestConfig);
    },

    /**
     * POST request with JSON body
     */
    post: <T = any>(url: string, body?: any): Promise<T> => {
        return httpClient.post<T>(url, body);
    },

    /**
     * PUT request with JSON body
     */
    put: <T = any>(url: string, body?: any): Promise<T> => {
        return httpClient.put<T>(url, body);
    },

    /**
     * DELETE request
     */
    delete: <T = any>(url: string): Promise<T> => {
        return httpClient.delete<T>(url);
    },

    /**
     * Upload file using FormData
     */
    upload: <T = any>(url: string, formData: FormData): Promise<T> => {
        return httpClient.upload<T>(url, formData);
    },

    /**
     * Login request without auth headers
     */
    login: <T = any>(url: string, body?: any): Promise<T> => {
        return httpClient.requestWithoutAuth<T>('POST', url, body);
    },
};

// Re-export httpClient for direct usage in new code
export { httpClient } from './httpClient';
export type { HttpClientConfig, RequestConfig, HttpResponse, HttpError } from './httpClient';
