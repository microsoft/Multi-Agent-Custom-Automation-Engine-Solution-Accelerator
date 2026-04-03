/**
 * API Client — thin adapter over the centralized httpClient.
 * 
 * Auth headers (x-ms-client-principal-id, Authorization) are now injected
 * automatically by httpClient's request interceptor, eliminating all manual
 * headerBuilder() / localStorage.getItem('token') calls.
 */
import httpClient from './httpClient';
import { getApiUrl } from './config';

/**
 * Ensure httpClient's base URL stays in sync with the runtime config.
 * Called lazily on every request so it picks up late-initialized API_URL.
 */
function syncBaseUrl(): void {
    const apiUrl = getApiUrl();
    if (apiUrl && httpClient.getBaseUrl() !== apiUrl) {
        httpClient.setBaseUrl(apiUrl);
    }
}

export const apiClient = {
    get: <T = any>(url: string, config?: { params?: Record<string, unknown> }): Promise<T> => {
        syncBaseUrl();
        return httpClient.get<T>(url, { params: config?.params });
    },

    post: <T = any>(url: string, body?: unknown): Promise<T> => {
        syncBaseUrl();
        return httpClient.post<T>(url, body);
    },

    put: <T = any>(url: string, body?: unknown): Promise<T> => {
        syncBaseUrl();
        return httpClient.put<T>(url, body);
    },

    delete: <T = any>(url: string): Promise<T> => {
        syncBaseUrl();
        return httpClient.del<T>(url);
    },

    upload: <T = any>(url: string, formData: FormData): Promise<T> => {
        syncBaseUrl();
        return httpClient.upload<T>(url, formData);
    },

    login: <T = any>(url: string, body?: unknown): Promise<T> => {
        syncBaseUrl();
        return httpClient.postWithoutAuth<T>(url, body);
    },
};
