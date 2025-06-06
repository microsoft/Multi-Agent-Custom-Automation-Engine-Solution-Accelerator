/**
 * Get a user-friendly error message based on the error type
 * @param error The error object to process
 * @returns User-friendly error message
 */
export const getErrorMessage = (error: unknown): string => {
    if (error instanceof Error) {
        // Check error message patterns for different types of errors
        const message = error.message.toLowerCase();

        if (message.includes('400') || message.includes('bad request')) {
            return `Bad request: ${error.message}`;
        } else if (message.includes('401') || message.includes('unauthorized')) {
            return 'You are not authorized to perform this action. Please sign in again.';
        } else if (message.includes('404') || message.includes('not found')) {
            return `Resource not found: ${error.message}`;
        } else if (message.includes('500') || message.includes('server error')) {
            return `Server error: ${error.message}. Please try again later.`;
        } else if (message.includes('network') || message.includes('fetch')) {
            return 'Network error. Please check your connection and try again.';
        }

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
    if (error instanceof Error) {
        const message = error.message.toLowerCase();

        if (message.includes('400') || message.includes('bad request')) {
            return 'error-bad-request';
        } else if (message.includes('401') || message.includes('unauthorized')) {
            return 'error-unauthorized';
        } else if (message.includes('404') || message.includes('not found')) {
            return 'error-not-found';
        } else if (message.includes('500') || message.includes('server error')) {
            return 'error-server';
        }
    }
    return 'error-general';
};
