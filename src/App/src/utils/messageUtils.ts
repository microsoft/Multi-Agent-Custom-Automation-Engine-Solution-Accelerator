/**
 * Message Utility Functions
 *
 * Extracted formatting helpers that were previously inline in PlanPage
 * and streaming components.
 */

/**
 * Format an error message for display in the chat panel.
 * Adds a warning emoji prefix and indentation for multi-line errors.
 */
export function formatErrorMessage(content: string): string {
    const lines = content.split('\n');
    return lines
        .map((line, idx) => {
            if (idx === 0) return `\u26A0\uFE0F ${line}`;
            if (line.trim() === '') return '';
            return `&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;${line}`;
        })
        .join('\n');
}

/**
 * Extract a plain-text answer from a potentially markdown-wrapped string.
 * Strips leading/trailing whitespace and common markdown wrappers.
 */
export function extractPlainAnswer(raw: string): string {
    if (!raw) return '';
    let text = raw.trim();
    // Strip markdown code block wrappers
    if (text.startsWith('```') && text.endsWith('```')) {
        text = text.slice(3, -3).trim();
        // Remove optional language hint on first line
        const firstNewline = text.indexOf('\n');
        if (firstNewline > -1 && firstNewline < 20) {
            text = text.slice(firstNewline + 1).trim();
        }
    }
    return text;
}

/**
 * Truncate a string to maxLen characters, appending "…" if truncated.
 */
export function truncate(str: string, maxLen: number): string {
    if (!str || str.length <= maxLen) return str;
    return str.slice(0, maxLen - 1) + '\u2026';
}
