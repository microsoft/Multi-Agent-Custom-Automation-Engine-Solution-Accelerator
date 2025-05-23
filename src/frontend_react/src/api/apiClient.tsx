import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

export interface ApiError {
    status: number;
    message: string;
    data?: any;
}

// Define classes for different error types
export class BadRequestError extends Error {
    public readonly status = 400;
    public readonly data?: any;

    constructor(message: string, data?: any) {
        super(message);
        this.name = 'BadRequestError';
        this.data = data;
    }
}

export class UnauthorizedError extends Error {
    public readonly status = 401;
    public readonly data?: any;

    constructor(message: string, data?: any) {
        super(message);
        this.name = 'UnauthorizedError';
        this.data = data;
    }
}

export class NotFoundError extends Error {
    public readonly status = 404;
    public readonly data?: any;

    constructor(message: string, data?: any) {
        super(message);
        this.name = 'NotFoundError';
        this.data = data;
    }
}

export class ServerError extends Error {
    public readonly status = 500;
    public readonly data?: any;

    constructor(message: string, data?: any) {
        super(message);
        this.name = 'ServerError';
        this.data = data;
    }
}

export class ApiClient {
    private client: AxiosInstance;

    constructor(baseURL: string) {
        this.client = axios.create({
            baseURL,
            headers: {
                'Content-Type': 'application/json',
            },
            withCredentials: true, // Include credentials for cross-origin requests if needed
        });

        // Add request interceptor to handle authentication
        this.client.interceptors.request.use(
            (config) => {
                // Get token from localStorage or other storage mechanism
                const token = localStorage.getItem('authToken');
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        // Add response interceptor to handle errors
        this.client.interceptors.response.use(
            (response) => response,
            (error: AxiosError) => {
                const { response } = error;

                if (!response) {
                    return Promise.reject(new ServerError('Network error or server is not responding'));
                }

                const { status, data } = response;
                const message = data?.detail || data?.message || 'An error occurred';

                switch (status) {
                    case 400:
                        return Promise.reject(new BadRequestError(message, data));
                    case 401:
                        // Optionally clear auth state here
                        return Promise.reject(new UnauthorizedError(message, data));
                    case 404:
                        return Promise.reject(new NotFoundError(message, data));
                    case 500:
                        return Promise.reject(new ServerError(message, data));
                    default:
                        return Promise.reject(new Error(`Unexpected error: ${message}`));
                }
            }
        );
    }

    async get<T>(path: string, config?: AxiosRequestConfig): Promise<T> {
        const response: AxiosResponse<T> = await this.client.get(path, config);
        return response.data;
    }

    async post<T>(path: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
        const response: AxiosResponse<T> = await this.client.post(path, data, config);
        return response.data;
    }

    async put<T>(path: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
        const response: AxiosResponse<T> = await this.client.put(path, data, config);
        return response.data;
    }

    async delete<T>(path: string, config?: AxiosRequestConfig): Promise<T> {
        const response: AxiosResponse<T> = await this.client.delete(path, config);
        return response.data;
    }

    async patch<T>(path: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
        const response: AxiosResponse<T> = await this.client.patch(path, data, config);
        return response.data;
    }
}

// Create and export a default API client instance
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';
export const apiClient = new ApiClient(API_BASE_URL);
