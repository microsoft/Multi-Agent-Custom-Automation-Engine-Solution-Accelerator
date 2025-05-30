import { useState, useCallback } from 'react';
import { BadRequestError, NotFoundError, ServerError, UnauthorizedError } from '../api/apiClient';

interface ApiHookState<T> {
    data: T | null;
    loading: boolean;
    error: Error | null;
}

interface ApiHookReturn<T> extends ApiHookState<T> {
    execute: (...args: any[]) => Promise<T | null>;
    reset: () => void;
}

/**
 * Custom hook for handling API requests with loading, error, and data states
 * @param apiFunction The API function to call
 * @returns Object containing data, loading, error states and execute function
 */
export function useApi<T>(
    apiFunction: (...args: any[]) => Promise<T>
): ApiHookReturn<T> {
    const [state, setState] = useState<ApiHookState<T>>({
        data: null,
        loading: false,
        error: null,
    });

    const execute = useCallback(
        async (...args: any[]): Promise<T | null> => {
            setState({ data: null, loading: true, error: null });
            try {
                const result = await apiFunction(...args);
                setState({ data: result, loading: false, error: null });
                return result;
            } catch (error) {
                let errorToSet: Error;

                if (error instanceof BadRequestError ||
                    error instanceof UnauthorizedError ||
                    error instanceof NotFoundError ||
                    error instanceof ServerError) {
                    errorToSet = error;
                } else {
                    errorToSet = new Error(
                        error instanceof Error ? error.message : 'An unknown error occurred'
                    );
                }

                setState({ data: null, loading: false, error: errorToSet });
                return null;
            }
        },
        [apiFunction]
    );

    const reset = useCallback(() => {
        setState({ data: null, loading: false, error: null });
    }, []);

    return { ...state, execute, reset };
}
