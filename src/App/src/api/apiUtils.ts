/**
 * API Utility Functions
 * 
 * Centralized helpers for error response construction, retry logic,
 * and request deduplication. Single source of truth — eliminates
 * duplicated error patterns across API functions.
 */

/**
 * Create a standardized error response object.
 * Replaces repeated `{ ...new Response(), ok: false, status: 500 }` patterns.
 */
export function createErrorResponse(status: number, message: string): Response {
    return new Response(JSON.stringify({ error: message }), {
        status,
        statusText: message,
        headers: { 'Content-Type': 'application/json' },
    });
}

/**
 * Retry a request with exponential backoff.
 * @param fn - The async function to retry
 * @param maxRetries - Maximum number of retry attempts (default: 3)
 * @param baseDelay - Base delay in ms before exponential increase (default: 1000)
 */
export async function retryRequest<T>(
    fn: () => Promise<T>,
    maxRetries = 3,
    baseDelay = 1000
): Promise<T> {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            if (attempt === maxRetries) throw error;
            const delay = baseDelay * Math.pow(2, attempt);
            await new Promise((resolve) => setTimeout(resolve, delay));
        }
    }
    throw new Error('Max retries exceeded');
}

/**
 * Request cache with TTL and deduplication of in-flight requests.
 * Prevents duplicate API calls for the same data.
 */
interface CacheEntry<T> {
    data: T;
    timestamp: number;
    expiresAt: number;
}

export class RequestCache {
    private cache = new Map<string, CacheEntry<unknown>>();
    private pendingRequests = new Map<string, Promise<unknown>>();

    /** Get cached data or fetch it, deduplicating concurrent identical requests */
    async get<T>(
        key: string,
        fetcher: () => Promise<T>,
        ttlMs = 30000
    ): Promise<T> {
        // Return cached data if still fresh
        const cached = this.cache.get(key);
        if (cached && Date.now() < cached.expiresAt) {
            return cached.data as T;
        }

        // Deduplicate concurrent identical requests
        const pending = this.pendingRequests.get(key);
        if (pending) {
            return pending as Promise<T>;
        }

        const request = fetcher()
            .then((data) => {
                this.cache.set(key, {
                    data,
                    timestamp: Date.now(),
                    expiresAt: Date.now() + ttlMs,
                });
                this.pendingRequests.delete(key);
                return data;
            })
            .catch((error) => {
                this.pendingRequests.delete(key);
                throw error;
            });

        this.pendingRequests.set(key, request);
        return request;
    }

    /** Invalidate cached entries matching a key pattern */
    invalidate(pattern?: string | RegExp): void {
        if (!pattern) {
            this.cache.clear();
            return;
        }
        for (const key of this.cache.keys()) {
            const matches = typeof pattern === 'string'
                ? key.includes(pattern)
                : pattern.test(key);
            if (matches) this.cache.delete(key);
        }
    }

    /** Clear all cached data */
    clear(): void {
        this.cache.clear();
        this.pendingRequests.clear();
    }
}

/** Shared request cache singleton */
export const requestCache = new RequestCache();

/**
 * Debounce utility — delays calling `fn` until `delayMs` has elapsed
 * since the last invocation.
 */
export function debounce<T extends (...args: unknown[]) => void>(
    fn: T,
    delayMs: number
): (...args: Parameters<T>) => void {
    let timer: ReturnType<typeof setTimeout>;
    return (...args: Parameters<T>) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delayMs);
    };
}

/**
 * Throttle utility — ensures `fn` is called at most once per `limitMs`.
 */
export function throttle<T extends (...args: unknown[]) => void>(
    fn: T,
    limitMs: number
): (...args: Parameters<T>) => void {
    let lastCall = 0;
    return (...args: Parameters<T>) => {
        const now = Date.now();
        if (now - lastCall >= limitMs) {
            lastCall = now;
            fn(...args);
        }
    };
}
