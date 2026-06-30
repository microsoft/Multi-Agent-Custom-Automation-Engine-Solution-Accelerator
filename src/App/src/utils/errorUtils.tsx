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
            return 'Invalid request. Please check your input and try again.';
        } else if (message.includes('401') || message.includes('unauthorized')) {
            return 'You are not authorized to perform this action. Please sign in again.';
        } else if (message.includes('404') || message.includes('not found')) {
            return 'The requested resource was not found.';
        } else if (message.includes('429') || message.includes('too many requests')) {
            return 'Too many requests. Please wait a moment and try again.';
        } else if (message.includes('500') || message.includes('server error')) {
            return 'A server error occurred. Please try again later.';
        } else if (message.includes('network') || message.includes('fetch')) {
            return 'Network error. Please check your connection and try again.';
        } else if (message.includes('timeout')) {
            return 'Request timed out. Please try again.';
        } else if (message.includes('quota') || message.includes('limit')) {
            return 'Service limit reached. Please try again later.';
        }

        // Return original message if it's already user-friendly (doesn't contain technical terms)
        if (!message.includes('exception') && !message.includes('stack') && 
            !message.includes('undefined') && !message.includes('null')) {
            return error.message;
        }
    }
    return 'An unexpected error occurred. Please try again.';
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
