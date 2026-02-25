import { useEffect, useState } from "react";

/**
 * Hook that debounces a value by the specified delay.
 *
 * Returns the debounced value — it only updates after the caller's
 * `value` has been stable for `delay` milliseconds.
 *
 * @param value - the raw value to debounce
 * @param delay - debounce delay in ms (default: 300)
 */
export function useDebounce<T>(value: T, delay = 300): T {
    const [debouncedValue, setDebouncedValue] = useState<T>(value);

    useEffect(() => {
        const timer = setTimeout(() => setDebouncedValue(value), delay);
        return () => clearTimeout(timer);
    }, [value, delay]);

    return debouncedValue;
}

export default useDebounce;
