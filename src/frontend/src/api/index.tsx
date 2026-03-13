// Export our API services and utilities
export * from './apiClient';

// Centralized HTTP client with interceptors (Point 2)
export { default as httpClient } from './httpClient';

// API utilities: createErrorResponse, retryRequest, RequestCache (Points 6, 8)
export * from './apiUtils';

// Unified API service - recommended for all new code
export { apiService } from './apiService';
