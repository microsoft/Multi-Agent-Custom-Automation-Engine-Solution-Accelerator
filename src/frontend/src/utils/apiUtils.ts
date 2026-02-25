/**
 * API-Level Utilities — Caching & Request Deduplication
 *
 * General-purpose classes extracted from the APIService layer so they can be
 * reused across any service that needs in-memory caching or request
 * deduplication.
 */

// ─── Types ───────────────────────────────────────────────────────────────────

/** Internal shape of a cache entry – not exported. */
interface CacheEntry<T> {
    data: T;
    timestamp: number;
    ttl: number; // Time to live in ms
}

// ─── RequestCache ────────────────────────────────────────────────────────────

/**
 * Simple in-memory TTL cache for API responses.
 *
 * @example
 * ```ts
 * const cache = new RequestCache();
 * cache.set('plans_all', data, 30_000);      // cache for 30 s
 * const cached = cache.get<Plan[]>('plans_all');
 * cache.invalidate(/^plans_/);               // clear matching keys
 * ```
 */
export class RequestCache {
    private cache: Map<string, CacheEntry<any>> = new Map();

    /** Store a value under `key` with an optional TTL (default 60 s). */
    set<T>(key: string, data: T, ttl = 60_000): void {
        this.cache.set(key, { data, timestamp: Date.now(), ttl });
    }

    /** Retrieve a value if it exists and has not expired; otherwise `null`. */
    get<T>(key: string): T | null {
        const entry = this.cache.get(key);
        if (!entry) return null;

        if (Date.now() - entry.timestamp > entry.ttl) {
            this.cache.delete(key);
            return null;
        }

        return entry.data;
    }

    /** Remove all entries. */
    clear(): void {
        this.cache.clear();
    }

    /** Remove all entries whose key matches `pattern`. */
    invalidate(pattern: RegExp): void {
        for (const key of this.cache.keys()) {
            if (pattern.test(key)) {
                this.cache.delete(key);
            }
        }
    }
}

// ─── RequestTracker ──────────────────────────────────────────────────────────

/**
 * Deduplicates in-flight requests: if the same logical request is triggered
 * multiple times before the first one resolves, every caller receives the
 * same promise instead of firing a duplicate network call.
 *
 * @example
 * ```ts
 * const tracker = new RequestTracker();
 * const plans = await tracker.trackRequest('plans', () => api.getPlans());
 * ```
 */
export class RequestTracker {
    private pendingRequests: Map<string, Promise<any>> = new Map();

    /**
     * If a request with `key` is already in-flight, return the existing
     * promise. Otherwise execute `requestFn`, track it, and clean up when
     * done.
     */
    async trackRequest<T>(key: string, requestFn: () => Promise<T>): Promise<T> {
        if (this.pendingRequests.has(key)) {
            return this.pendingRequests.get(key)!;
        }

        const requestPromise = requestFn();
        this.pendingRequests.set(key, requestPromise);

        try {
            return await requestPromise;
        } finally {
            this.pendingRequests.delete(key);
        }
    }
}
