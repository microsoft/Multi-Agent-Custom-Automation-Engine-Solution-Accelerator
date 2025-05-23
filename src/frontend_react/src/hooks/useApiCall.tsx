import { useState, useCallback } from 'react';
import { apiService } from '../api/apiService';
import { BadRequestError, NotFoundError, ServerError, UnauthorizedError } from '../api/apiClient';

interface ApiCallState<T> {
    data: T | null;
    loading: boolean;
    error: Error | null;
}

interface ApiCallOptions {
    /**
     * Whether to use cached data if available
     */
    useCache?: boolean;
    /**
     * Whether to automatically clear any errors when executing the function again
     */
    clearErrorOnCall?: boolean;
    /**
     * Callback that runs after a successful API call
     */
    onSuccess?: (data: any) => void;
    /**
     * Callback that runs after a failed API call
     */
    onError?: (error: Error) => void;
}

/**
 * A custom hook that wraps API calls from our unified apiService
 * 
 * @param apiMethod The API method to call from apiService
 * @param options Additional options for controlling behavior
 * @returns Object containing data, loading, error states and execute function
 */
function useApiCall<T, A extends any[]>(
    apiMethod: (...args: A) => Promise<T>,
    options: ApiCallOptions = {}
) {
    const {
        useCache = true,
        clearErrorOnCall = true,
        onSuccess,
        onError
    } = options;

    const [state, setState] = useState<ApiCallState<T>>({
        data: null,
        loading: false,
        error: null,
    });

    const execute = useCallback(
        async (...args: A): Promise<T | null> => {
            if (clearErrorOnCall && state.error) {
                setState(prevState => ({
                    ...prevState,
                    error: null
                }));
            }

            setState(prevState => ({
                ...prevState,
                loading: true
            }));

            try {
                // Pass the useCache option as the last argument if the method supports it
                const apiArgs = [...args] as any[];
                const methodName = apiMethod.name;

                // Check if this method supports caching
                const methodsSupportingCache = [
                    'getPlans',
                    'getPlanWithSteps',
                    'getSteps',
                    'getAgentMessages',
                    'getAllMessages'
                ];

                // Only add useCache parameter if the method supports it
                if (methodsSupportingCache.some(name => methodName.includes(name))) {
                    // Replace the last argument with useCache if it's a boolean
                    if (typeof apiArgs[apiArgs.length - 1] === 'boolean') {
                        apiArgs[apiArgs.length - 1] = useCache;
                    } else {
                        apiArgs.push(useCache);
                    }
                }

                const result = await apiMethod(...apiArgs as any);
                setState({
                    data: result,
                    loading: false,
                    error: null
                });

                if (onSuccess) {
                    onSuccess(result);
                }

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

                setState({
                    data: null,
                    loading: false,
                    error: errorToSet
                });

                if (onError) {
                    onError(errorToSet);
                }

                return null;
            }
        },
        [apiMethod, clearErrorOnCall, onError, onSuccess, state.error, useCache]
    );

    const reset = useCallback(() => {
        setState({
            data: null,
            loading: false,
            error: null
        });
    }, []);

    return {
        ...state,
        execute,
        reset
    };
}

/**
 * Utility function to create an API call hook for a specific apiService method
 * 
 * @param methodKey The method name from apiService
 * @returns A custom hook for that specific API method
 */
export function createApiHook<T, A extends any[]>(
    methodKey: keyof typeof apiService
): (options?: ApiCallOptions) => {
    data: T | null;
    loading: boolean;
    error: Error | null;
    execute: (...args: A) => Promise<T | null>;
    reset: () => void;
} {
    return (options: ApiCallOptions = {}) => {
        const method = apiService[methodKey] as (...args: A) => Promise<T>;
        return useApiCall<T, A>(method, options);
    };
}

// Create pre-configured hooks for common API operations
export const useGetPlans = createApiHook<any[], [string?]>('getPlans');
export const useGetPlanWithSteps = createApiHook<any, [string, string]>('getPlanWithSteps');
export const useGetSteps = createApiHook<any[], [string]>('getSteps');
export const useSubmitInputTask = createApiHook<any, [any]>('submitInputTask');
export const useSubmitClarification = createApiHook<any, [string, string, string]>('submitClarification');
export const useGetAgentMessages = createApiHook<any[], [string]>('getAgentMessages');

export default useApiCall;
