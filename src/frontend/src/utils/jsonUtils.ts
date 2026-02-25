/**
 * JSON & Python-repr Parsing Utilities
 *
 * Helpers for safely parsing JSON, unescaping Python repr strings, and
 * extracting structured fields from repr-formatted objects received from
 * the backend.
 */

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * Safely parse a JSON string, returning `fallback` (default `null`) on
 * failure instead of throwing.
 *
 * @example
 * ```ts
 * const obj = parseJsonSafe<Plan>(rawString, { id: '', status: '' });
 * ```
 */
export function parseJsonSafe<T = any>(
    raw: string,
    fallback: T | null = null
): T | null {
    try {
        return JSON.parse(raw) as T;
    } catch {
        return fallback;
    }
}

/**
 * Unescape common Python-repr escape sequences found in backend payloads.
 *
 * Converts `\\n` → newline, `\\'` → `'`, `\\"` → `"`, `\\\\` → `\`,
 * `\\u200b` → (removes zero-width spaces).
 */
export function unescapeReprString(s: string): string {
    return s
        .replace(/\\n/g, '\n')
        .replace(/\\'/g, "'")
        .replace(/\\"/g, '"')
        .replace(/\\\\/g, '\\')
        .replace(/\\u200b/g, '');
}

/**
 * Clean markdown formatting and boilerplate prefixes from action text.
 *
 * Used when converting MStep / MPlan actions into human-readable strings.
 */
export function cleanActionText(action: string): string {
    return action
        .replace(/\*\*/g, '')                                                   // Remove markdown bold
        .replace(/^Certainly!\s*/i, '')
        .replace(/^Given the team composition and the available facts,?\s*/i, '')
        .replace(/^here is a (?:concise )?plan to[^.]*\.\s*/i, '')
        .replace(/^(?:here is|this is) a (?:concise )?(?:plan|approach|strategy)[^.]*[.:]\s*/i, '')
        .replace(/^\*\*([^*]+)\*\*:?\s*/g, '$1: ')
        .replace(/^[-•]\s*/, '')
        .replace(/\s+/g, ' ')
        .trim();
}

/**
 * Extract a single-quoted or double-quoted field value from a Python repr
 * string.
 *
 * @example
 * ```ts
 * extractReprField("MPlan(id='abc', ...)", 'id');  // → 'abc'
 * ```
 *
 * @internal — only used within this module and PlanDataService
 */
export function extractReprField(
    source: string,
    fieldName: string,
    toUpperCase = false
): string | undefined {
    const re = new RegExp(`${fieldName}='([^']+)'|${fieldName}="([^"]+)"`);
    const m = source.match(re);
    if (!m) return undefined;
    const val = m[1] ?? m[2];
    return toUpperCase ? val.toUpperCase() : val;
}

/**
 * Try to parse a raw string as JSON first; if that fails treat it as a
 * Python-repr–formatted payload and return the original value for further
 * repr-specific parsing.
 *
 * Useful at the boundary where a WebSocket message arrives and may be
 * either format.
 */
export function tryParseJsonOrPassthrough<T = any>(raw: string): T | string {
    if (raw.startsWith('{') || raw.startsWith('[')) {
        try {
            return JSON.parse(raw) as T;
        } catch {
            // Not valid JSON – fall through
        }
    }
    return raw;
}
