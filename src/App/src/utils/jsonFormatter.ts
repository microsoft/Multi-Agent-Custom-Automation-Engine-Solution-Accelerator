/**
 * Utilities for detecting JSON / Python-dict style blocks embedded in
 * arbitrary text (streaming buffer, agent message content, etc.) and
 * rendering them as readable Markdown so they don't appear as raw JSON in
 * the UI.
 */

/**
 * Format a key from snake_case / camelCase / kebab-case into a readable label.
 */
const humanizeKey = (key: string): string => {
    if (!key) return key;
    const spaced = key
        .replace(/[_-]+/g, ' ')
        .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
        .trim();
    return spaced.replace(/\b\w/g, (c) => c.toUpperCase());
};

/**
 * Render a parsed JSON value as readable Markdown (bullet list of
 * "**Key**: value" entries, recursing into nested objects/arrays).
 */
export const jsonToMarkdown = (value: any, depth = 0): string => {
    const indent = '  '.repeat(depth);

    if (value === null || value === undefined) return `${indent}_n/a_`;

    if (Array.isArray(value)) {
        if (value.length === 0) return `${indent}_(none)_`;
        return value
            .map((item) => {
                if (item !== null && typeof item === 'object') {
                    return `${indent}- \n${jsonToMarkdown(item, depth + 1)}`;
                }
                return `${indent}- ${String(item)}`;
            })
            .join('\n');
    }

    if (typeof value === 'object') {
        const entries = Object.entries(value);
        if (entries.length === 0) return `${indent}_(empty)_`;
        return entries
            .map(([k, v]) => {
                const label = humanizeKey(k);
                if (v !== null && typeof v === 'object') {
                    return `${indent}- **${label}:**\n${jsonToMarkdown(v, depth + 1)}`;
                }
                return `${indent}- **${label}:** ${v === null || v === undefined ? '' : String(v)}`;
            })
            .join('\n');
    }

    return `${indent}${String(value)}`;
};

/**
 * Find the end index (inclusive) of a balanced JSON/dict value that starts
 * at `content[startIdx]`. Walks the string character-by-character tracking
 * string-literal context (both single- and double-quoted) and escape
 * sequences, so braces/brackets that appear inside string values do not
 * affect the depth count. Returns `-1` if no balanced value can be found.
 */
const findJsonEnd = (content: string, startIdx: number): number => {
    const open = content[startIdx];
    if (open !== '{' && open !== '[') return -1;
    const close = open === '{' ? '}' : ']';

    let depth = 0;
    let inString = false;
    let stringChar = '';
    let escape = false;

    for (let i = startIdx; i < content.length; i++) {
        const ch = content[i];

        if (inString) {
            if (escape) {
                escape = false;
            } else if (ch === '\\') {
                escape = true;
            } else if (ch === stringChar) {
                inString = false;
            }
            continue;
        }

        if (ch === '"' || ch === "'") {
            inString = true;
            stringChar = ch;
            continue;
        }

        if (ch === '{' || ch === '[') {
            depth++;
        } else if (ch === '}' || ch === ']') {
            depth--;
            if (depth === 0) {
                return ch === close ? i : -1;
            }
        }
    }

    return -1;
};

/**
 * Convert a Python-dict / Python-repr style string into a strict JSON string
 * so it can be parsed by `JSON.parse`. Walks character-by-character so that
 * single quotes inside double-quoted strings (and vice versa) and escape
 * sequences are preserved.
 *
 * Performs the following transformations on tokens *outside* string literals:
 *   - Replaces single-quoted string literals with double-quoted ones
 *     (escaping interior `"`).
 *   - Replaces `True` / `False` / `None` keywords with `true` / `false` / `null`.
 *   - Strips trailing commas before `}` or `]`.
 */
const normalizePythonDict = (input: string): string => {
    let out = '';
    let i = 0;
    const len = input.length;

    while (i < len) {
        const ch = input[i];

        // Double-quoted string — keep as-is, handle escapes
        if (ch === '"') {
            out += ch;
            i++;
            while (i < len) {
                const c = input[i];
                out += c;
                if (c === '\\' && i + 1 < len) {
                    out += input[i + 1];
                    i += 2;
                    continue;
                }
                if (c === '"') {
                    i++;
                    break;
                }
                i++;
            }
            continue;
        }

        // Single-quoted string — convert to double-quoted
        if (ch === "'") {
            out += '"';
            i++;
            while (i < len) {
                const c = input[i];
                if (c === '\\' && i + 1 < len) {
                    const next = input[i + 1];
                    if (next === "'") {
                        out += "'";
                    } else {
                        out += c + next;
                    }
                    i += 2;
                    continue;
                }
                if (c === "'") {
                    out += '"';
                    i++;
                    break;
                }
                if (c === '"') {
                    out += '\\"';
                    i++;
                    continue;
                }
                out += c;
                i++;
            }
            continue;
        }

        // Python keywords — only replace when at a word boundary
        const prev = i > 0 ? input[i - 1] : '';
        const isWordBoundary = !prev || !/[A-Za-z0-9_]/.test(prev);
        if (isWordBoundary) {
            if (input.startsWith('True', i) && !/[A-Za-z0-9_]/.test(input[i + 4] || '')) {
                out += 'true';
                i += 4;
                continue;
            }
            if (input.startsWith('False', i) && !/[A-Za-z0-9_]/.test(input[i + 5] || '')) {
                out += 'false';
                i += 5;
                continue;
            }
            if (input.startsWith('None', i) && !/[A-Za-z0-9_]/.test(input[i + 4] || '')) {
                out += 'null';
                i += 4;
                continue;
            }
        }

        out += ch;
        i++;
    }

    // Strip trailing commas: `, }` → ` }` and `, ]` → ` ]`
    return out.replace(/,(\s*[\]}])/g, '$1');
};

const tryParseJson = (block: string): any | null => {
    const trimmed = block.trim();
    if (!trimmed) return null;
    // Strict JSON first
    try {
        const parsed = JSON.parse(trimmed);
        if (parsed !== null && typeof parsed === 'object') return parsed;
    } catch {
        // fall through to fallback
    }
    // Python-dict / loose JSON fallback (single quotes, True/False/None, trailing commas)
    try {
        const normalized = normalizePythonDict(trimmed);
        const parsed = JSON.parse(normalized);
        if (parsed !== null && typeof parsed === 'object') return parsed;
    } catch {
        // ignore
    }
    return null;
};

/**
 * Detect raw JSON / Python-dict blocks anywhere in the input text and
 * replace each one with a readable Markdown rendering. Handles:
 *   - Bare JSON / dict values appearing mid-text
 *   - JSON inside fenced code blocks (```json ... ``` or ``` ... ```)
 *   - Python-style dicts with single quotes / True / False / None
 *   - Multiple independent blocks in the same buffer
 *
 * Uses a string-aware scanner so quotes and braces inside string values do
 * not throw off the balance count.
 */
export const formatJsonInText = (content: string): string => {
    if (!content) return content;

    let out = '';
    let i = 0;

    while (i < content.length) {
        const ch = content[i];

        // Handle a fenced code block beginning here
        if (ch === '`' && content.startsWith('```', i)) {
            const fenceStart = i;
            const lineEnd = content.indexOf('\n', i);
            const headerEnd = lineEnd === -1 ? content.length : lineEnd;
            const fenceLang = content.slice(i + 3, headerEnd).trim().toLowerCase();
            const closeIdx = content.indexOf('```', headerEnd);
            if (closeIdx === -1) {
                // Unterminated fence; emit the rest verbatim
                out += content.slice(i);
                i = content.length;
                continue;
            }
            const inner = content.slice(headerEnd + 1, closeIdx);
            const isJsonLang = fenceLang === 'json' || fenceLang === '' || fenceLang === 'python';
            if (isJsonLang) {
                const innerTrimmedStart = inner.search(/[{[]/);
                if (innerTrimmedStart !== -1) {
                    const endRel = findJsonEnd(inner, innerTrimmedStart);
                    if (endRel !== -1) {
                        const block = inner.slice(innerTrimmedStart, endRel + 1);
                        const parsed = tryParseJson(block);
                        if (parsed !== null) {
                            const prefix = inner.slice(0, innerTrimmedStart);
                            const suffix = inner.slice(endRel + 1);
                            if (prefix.trim()) out += prefix;
                            out += jsonToMarkdown(parsed) + '\n';
                            if (suffix.trim()) out += suffix;
                            i = closeIdx + 3;
                            continue;
                        }
                    }
                }
            }
            // Couldn't render as readable JSON — keep fenced block as-is
            out += content.slice(fenceStart, closeIdx + 3);
            i = closeIdx + 3;
            continue;
        }

        // Handle a bare JSON / dict value beginning here
        if (ch === '{' || ch === '[') {
            const endIdx = findJsonEnd(content, i);
            if (endIdx !== -1) {
                const block = content.slice(i, endIdx + 1);
                const parsed = tryParseJson(block);
                if (parsed !== null) {
                    out += jsonToMarkdown(parsed) + '\n';
                    i = endIdx + 1;
                    continue;
                }
            }
        }

        out += ch;
        i++;
    }

    return out;
};
