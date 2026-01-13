import { useState, useCallback } from 'react';
import { RAIErrorData } from '../components/errors';

export interface UseRAIErrorHandling {
    raiError: RAIErrorData | null;
    setRAIError: (error: RAIErrorData | null) => void;
    handleError: (error: any) => boolean; // Returns true if it was an RAI error
    clearRAIError: () => void;
}

/**
 * Custom hook for handling RAI (Responsible AI) validation errors
 * Provides standardized error parsing and state management
 */
export const useRAIErrorHandling = (): UseRAIErrorHandling => {
    const [raiError, setRAIError] = useState<RAIErrorData | null>(null);

    const clearRAIError = useCallback(() => {
        setRAIError(null);
    }, []);

    const handleError = useCallback((error: any): boolean => {
        // Clear any previous RAI errors
        setRAIError(null);

        // Check if this is an RAI validation error
        let errorDetail = null;
        try {
            // Try to parse the error detail if it's a string
            if (typeof error?.response?.data?.detail === 'string') {
                errorDetail = JSON.parse(error.response.data.detail);
            } else {
                errorDetail = error?.response?.data?.detail;
            }
        } catch (parseError) {
            // If parsing fails, use the original error
            errorDetail = error?.response?.data?.detail;
        }

        // Handle RAI validation errors
        if (errorDetail?.error_type === 'RAI_VALIDATION_FAILED') {
            setRAIError(errorDetail);
            return true; // Indicates this was an RAI error
        }

        return false; // Indicates this was not an RAI error
    }, []);

    return {
        raiError,
        setRAIError,
        handleError,
        clearRAIError
    };
};

export default useRAIErrorHandling;
