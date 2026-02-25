/**
 * Error Handling Utilities
 *
 * Single-source-of-truth helpers for extracting user-friendly error messages
 * from HttpError responses and formatting error content for display.
 */

// ─── HttpError Detail Extraction ─────────────────────────────────────────────

/**
 * Extract a user-friendly error message from an HttpError thrown by httpClient.
 *
 * The httpClient normalises errors into `{ data, status, statusText, message }`.
 * Backend FastAPI endpoints typically return `{ detail: "..." }` in the body.
 *
 * Resolution order:
 *  1. `error.data.detail` (string)  — FastAPI detail
 *  2. `error.data.detail` (object)  — nested `.detail`, `.message`, or JSON
 *  3. `error.data` (object)         — fallback `.detail`, `.message`, or JSON
 *  4. `error.message` (string)      — JS Error.message (unless it's "[object Object]")
 *  5. `fallback`                    — caller-provided default
 *
 * @param error     - the caught error (typed `any` for flexibility)
 * @param fallback  - default message when nothing useful can be extracted
 */
export function extractHttpErrorMessage(
    error: any,
    fallback = 'An unexpected error occurred'
): string {
    // 1. Try error.data?.detail as string
    if (typeof error?.data?.detail === 'string') {
        return error.data.detail;
    }

    // 2. Try error.data?.detail as object, then error.data itself
    const rawDetail = error?.data?.detail ?? error?.data;
    if (typeof rawDetail === 'object' && rawDetail !== null) {
        const nested = rawDetail.detail || rawDetail.message;
        if (typeof nested === 'string') return nested;
        try {
            const str = JSON.stringify(rawDetail);
            if (str && str !== '{}') return str;
        } catch { /* fall through */ }
    }

    // 3. Try error.message (JS Error), skip "[object Object]"
    if (
        typeof error?.message === 'string' &&
        error.message !== '[object Object]'
    ) {
        return error.message;
    }

    // 4. Fallback
    return fallback;
}

// ─── Error Content Classification ────────────────────────────────────────────

/** Returns true when the error message indicates RAI content-policy failure. */
export function isRaiError(message: string): boolean {
    return message.includes('inappropriate content');
}

/** Returns true when the error message indicates search-index validation failure. */
export function isSearchValidationError(message: string): boolean {
    return message.includes('Search index validation failed');
}

// ─── Display Formatting ──────────────────────────────────────────────────────

/**
 * Format an error string for display in agent messages.
 *
 * - First line is prefixed with ⚠️
 * - Subsequent non-empty lines are indented
 *
 * @param content - raw error text (may contain newlines)
 */
export function formatErrorMessage(content: string): string {
    const lines = content.split('\n');
    const formattedLines = lines.map((line, index) => {
        if (index === 0) return `⚠️ ${line}`;
        if (line.trim() === '') return '';
        return `&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;${line}`;
    });
    return formattedLines.join('\n');
}

// ─── Deeply-Nested Content Extraction ────────────────────────────────────────

/**
 * Extract text content from a deeply-nested WebSocket error payload.
 *
 * Checks `data.data.content`, `data.content`, `content`, and bare string
 * in that order — returning the first non-empty trimmed string.
 *
 * @param message - the raw WebSocket error message object
 * @param fallback - default when no content can be found
 */
export function extractNestedContent(
    message: any,
    fallback = 'An unexpected error occurred. Please try again later.'
): string {
    const candidates: unknown[] = [
        message?.data?.data?.content,
        message?.data?.content,
        message?.content,
        typeof message === 'string' ? message : undefined,
    ];

    for (const candidate of candidates) {
        if (typeof candidate === 'string') {
            const trimmed = candidate.trim();
            if (trimmed.length > 0) return trimmed;
        }
    }

    return fallback;
}

