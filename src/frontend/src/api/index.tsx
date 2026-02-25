// Export our API services and utilities
export * from './apiClient';

// Centralized HTTP client with interceptors (recommended for new code)
export { httpClient, HttpClient } from './httpClient';
export type { HttpClientConfig, RequestConfig, HttpResponse, HttpError } from './httpClient';

// Unified API service - recommended for all new code
export { apiService } from './apiService';
