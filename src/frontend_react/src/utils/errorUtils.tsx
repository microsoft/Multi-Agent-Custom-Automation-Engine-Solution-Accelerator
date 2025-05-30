import {
    BadRequestError,
    NotFoundError,
    ServerError,
    UnauthorizedError
} from '../api/apiClient';

/**
 * Get a user-friendly error message based on the error type
 * @param error The error object to process
 * @returns User-friendly error message
 */
export const getErrorMessage = (error: unknown): string => {
    if (error instanceof BadRequestError) {
        return `Bad request: ${error.message}`;
    } else if (error instanceof UnauthorizedError) {
        return 'You are not authorized to perform this action. Please sign in again.';
    } else if (error instanceof NotFoundError) {
        return `Resource not found: ${error.message}`;
    } else if (error instanceof ServerError) {
        return `Server error: ${error.message}. Please try again later.`;
    } else if (error instanceof Error) {
        return error.message;
    }
    return 'An unknown error occurred. Please try again.';
};

/**
 * Get CSS class or style based on error type for UI elements
 * @param error The error object to process
 * @returns CSS class name or style object
 */
export const getErrorStyle = (error: unknown): string => {
    if (error instanceof BadRequestError) {
        return 'error-bad-request';
    } else if (error instanceof UnauthorizedError) {
        return 'error-unauthorized';
    } else if (error instanceof NotFoundError) {
        return 'error-not-found';
    } else if (error instanceof ServerError) {
        return 'error-server';
    }
    return 'error-general';
};
