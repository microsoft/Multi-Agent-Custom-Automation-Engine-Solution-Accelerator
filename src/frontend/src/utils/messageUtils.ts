/**
 * Message & Text Formatting Utilities
 *
 * Domain-specific helpers for cleaning, formatting and transforming
 * text that appears in agent messages, task displays and user-facing labels.
 */

import { AgentMessageData, AgentMessageType } from '../models';

// ─── Text Cleaning ───────────────────────────────────────────────────────────

/**
 * Clean text by converting camelCase / PascalCase to spaces, stripping
 * non-alphanumeric characters, and capitalising each word.
 *
 * Also normalises common agent name quirks (e.g. "Hr_Agent" → "HR Agent").
 *
 * @example
 * ```ts
 * cleanTextToSpaces('Hr_Agent');           // → 'HR Agent'
 * cleanTextToSpaces('dataOrderAnalysis');   // → 'Data Order Analysis'
 * ```
 */
export function cleanTextToSpaces(text: string): string {
    if (!text) return '';

    let cleaned = text
        .replace('Hr_Agent', 'HR Agent')
        .replace('Hr Agent', 'HR Agent')
        .trim();

    // camelCase / PascalCase → spaces
    cleaned = cleaned.replace(/([a-z])([A-Z])/g, '$1 $2');

    // Strip non-alphanumeric
    cleaned = cleaned.replace(/[^a-zA-Z0-9]/g, ' ');

    // Collapse whitespace
    cleaned = cleaned.replace(/\s+/g, ' ').trim();

    // Capitalise each word
    cleaned = cleaned.replace(/\b\w/g, char => char.toUpperCase());

    return cleaned;
}

/**
 * Normalise HR-specific agent name quirks.
 *
 * Lighter-weight than {@link cleanTextToSpaces} — only fixes known
 * variations of "Hr_Agent" / "Hr Agent" without altering other text.
 */
export function cleanHRAgentText(text: string): string {
    if (!text) return '';
    return text
        .replace('Hr_Agent', 'HR Agent')
        .replace('Hr Agent', 'HR Agent')
        .trim();
}

// ─── Date Formatting ─────────────────────────────────────────────────────────

/**
 * Format a date according to the provided format string.
 *
 * Supported tokens:
 *  YYYY, YY, MMM, MM, M, DD, D, HH, H, hh, h, mm, m, A
 *
 * When `format` is omitted the system locale format is used.
 */
export function formatDate(
    date: Date | string | number,
    format?: string
): string {
    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) return '';

    if (!format) {
        return d.toLocaleString();
    }

    const pad = (n: number, len = 2) => n.toString().padStart(len, '0');
    const hours12 = d.getHours() % 12 || 12;
    const ampm = d.getHours() < 12 ? 'AM' : 'PM';

    const replacements: Record<string, string> = {
        YYYY: d.getFullYear().toString(),
        YY: d.getFullYear().toString().slice(-2),
        MMM: monthsShort[d.getMonth()],
        MM: pad(d.getMonth() + 1),
        M: (d.getMonth() + 1).toString(),
        DD: pad(d.getDate()),
        D: d.getDate().toString(),
        HH: pad(d.getHours()),
        H: d.getHours().toString(),
        hh: pad(hours12),
        h: hours12.toString(),
        mm: pad(d.getMinutes()),
        m: d.getMinutes().toString(),
        A: ampm,
    };

    let formatted = format;
    Object.entries(replacements)
        .sort(([a], [b]) => b.length - a.length) // longer tokens first
        .forEach(([token, value]) => {
            formatted = formatted.replace(new RegExp(token, 'g'), value);
        });

    return formatted;
}

// ─── Internal helpers (non-exported) ─────────────────────────────────────────

/** Abbreviated month names used by formatDate. */
const monthsShort = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
];

// ─── AgentMessageData Factory ────────────────────────────────────────────────

/**
 * Create a well-typed `AgentMessageData` object.
 *
 * Replaces the 4+ manual `{ agent, agent_type, timestamp, steps: [], … }`
 * constructions scattered across hooks and components.
 *
 * @param agent     - agent name / identifier (e.g. "human", "system", AgentType.GROUP_CHAT_MANAGER)
 * @param agentType - discriminator from AgentMessageType enum
 * @param content   - display text for the message
 * @param rawData   - raw payload to attach (string or serialised object)
 * @param timestamp - optional epoch ms (defaults to Date.now())
 */
export function createAgentMessage(
    agent: string,
    agentType: AgentMessageType,
    content: string,
    rawData: any = '',
    timestamp: number = Date.now()
): AgentMessageData {
    return {
        agent,
        agent_type: agentType,
        timestamp,
        steps: [],
        next_steps: [],
        content,
        raw_data: rawData,
    };
}
