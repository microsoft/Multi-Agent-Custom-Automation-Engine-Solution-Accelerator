/**
 * HTTP Production Utilities
 *
 * Domain-specific utilities that complement the centralized HttpClient:
 *  - retryRequest  — retry any async operation with exponential backoff
 *  - throttle      — limit how often a function can fire
 *  - debounce      — delay execution until input settles
 */

// ─── Types ───────────────────────────────────────────────────────────────────

export interface RetryOptions {
    /** Maximum number of retry attempts (default: 3) */
    maxRetries?: number;
    /** Initial delay in ms before the first retry (default: 1000) */
    baseDelay?: number;
    /** Maximum delay cap in ms (default: 30 000) */
    maxDelay?: number;
    /** Multiplier applied to the delay after each retry (default: 2) */
    backoffFactor?: number;
    /**
     * Optional predicate — return `true` to retry, `false` to bail out early.
     * Receives the caught error and the 1-based attempt number.
     */
    retryOn?: (error: unknown, attempt: number) => boolean;
}

// ─── retryRequest ────────────────────────────────────────────────────────────

/**
 * Retry an async operation with configurable exponential backoff and jitter.
 *
 * @example
 * ```ts
 * const data = await retryRequest(
 *   () => httpClient.get('/api/plans'),
 *   { maxRetries: 3, baseDelay: 500 }
 * );
 * ```
 */
export async function retryRequest<T>(
    fn: () => Promise<T>,
    options?: RetryOptions
): Promise<T> {
    const {
        maxRetries = 3,
        baseDelay = 1000,
        maxDelay = 30_000,
        backoffFactor = 2,
        retryOn,
    } = options ?? {};

    let lastError: unknown;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error;

            // Exhausted retries
            if (attempt === maxRetries) break;

            // Caller-provided bail-out
            if (retryOn && !retryOn(error, attempt + 1)) break;

            // Exponential backoff with jitter
            const exponentialDelay = baseDelay * Math.pow(backoffFactor, attempt);
            const jitter = Math.random() * baseDelay * 0.5;
            const delay = Math.min(exponentialDelay + jitter, maxDelay);

            await sleep(delay);
        }
    }

    throw lastError;
}

// ─── throttle ────────────────────────────────────────────────────────────────

export interface ThrottledFn<T extends (...args: any[]) => any> {
    (...args: Parameters<T>): void;
    /** Cancel any pending trailing invocation. */
    cancel: () => void;
}

/**
 * Create a throttled version of `fn` that fires at most once every `delay` ms.
 *
 * The first call executes immediately; subsequent calls within the window are
 * queued so the last invocation always runs when the window expires.
 */
export function throttle<T extends (...args: any[]) => any>(
    fn: T,
    delay: number
): ThrottledFn<T> {
    let lastCallTime = 0;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let lastArgs: Parameters<T> | null = null;

    const throttled = (...args: Parameters<T>): void => {
        const now = Date.now();
        const remaining = delay - (now - lastCallTime);

        if (remaining <= 0) {
            // Window elapsed → fire immediately
            if (timeoutId !== null) {
                clearTimeout(timeoutId);
                timeoutId = null;
            }
            lastCallTime = now;
            fn(...args);
        } else {
            // Inside the window → queue trailing call
            lastArgs = args;
            if (timeoutId === null) {
                timeoutId = setTimeout(() => {
                    lastCallTime = Date.now();
                    timeoutId = null;
                    if (lastArgs) {
                        fn(...lastArgs);
                        lastArgs = null;
                    }
                }, remaining);
            }
        }
    };

    throttled.cancel = () => {
        if (timeoutId !== null) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
        lastArgs = null;
    };

    return throttled as ThrottledFn<T>;
}

// ─── debounce ────────────────────────────────────────────────────────────────

export interface DebouncedFn<T extends (...args: any[]) => any> {
    (...args: Parameters<T>): void;
    /** Cancel any pending invocation. */
    cancel: () => void;
    /** Execute immediately if there is a pending invocation. */
    flush: () => void;
}

/**
 * Create a debounced version of `fn` that delays invocation until `delay` ms
 * have elapsed since the last call.
 *
 * Unlike the React `useDebounce` hook this is a plain function suitable for
 * non-React contexts (event handlers, service layers, etc.).
 */
export function debounce<T extends (...args: any[]) => any>(
    fn: T,
    delay: number
): DebouncedFn<T> {
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let lastArgs: Parameters<T> | null = null;

    const debounced = (...args: Parameters<T>): void => {
        lastArgs = args;
        if (timeoutId !== null) {
            clearTimeout(timeoutId);
        }
        timeoutId = setTimeout(() => {
            timeoutId = null;
            if (lastArgs) {
                fn(...lastArgs);
                lastArgs = null;
            }
        }, delay);
    };

    debounced.cancel = () => {
        if (timeoutId !== null) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
        lastArgs = null;
    };

    debounced.flush = () => {
        if (timeoutId !== null) {
            clearTimeout(timeoutId);
            timeoutId = null;
            if (lastArgs) {
                fn(...lastArgs);
                lastArgs = null;
            }
        }
    };

    return debounced as DebouncedFn<T>;
}

// ─── Internal helpers (non-exported) ─────────────────────────────────────────

/** Simple promise-based sleep used internally by retryRequest. */
function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}
