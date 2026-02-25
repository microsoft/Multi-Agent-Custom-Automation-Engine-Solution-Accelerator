/**
 * Chart Formatting & Data-Transformation Utilities
 *
 * Helpers for preparing numeric data for chart display.
 * Extend this module as charting requirements grow.
 */

// ─── Value Formatting ────────────────────────────────────────────────────────

/**
 * Format a number for chart axis / tooltip display.
 *
 * - Large values are abbreviated (1 200 → "1.2K", 3 500 000 → "3.5M").
 * - Small values use fixed-precision decimals.
 *
 * @param value     The numeric value to format
 * @param precision Decimal places for small values (default: 1)
 */
export function formatChartValue(value: number, precision = 1): string {
    if (Math.abs(value) >= 1_000_000_000) {
        return (value / 1_000_000_000).toFixed(precision).replace(/\.0+$/, '') + 'B';
    }
    if (Math.abs(value) >= 1_000_000) {
        return (value / 1_000_000).toFixed(precision).replace(/\.0+$/, '') + 'M';
    }
    if (Math.abs(value) >= 1_000) {
        return (value / 1_000).toFixed(precision).replace(/\.0+$/, '') + 'K';
    }
    return value.toFixed(precision).replace(/\.0+$/, '');
}

// ─── Data Normalisation ──────────────────────────────────────────────────────

/**
 * Normalise an array of numbers to 0–100 percentage range.
 *
 * @param data Raw data points
 * @param min  Custom minimum (defaults to data min)
 * @param max  Custom maximum (defaults to data max)
 * @returns Normalised values in [0, 100]
 */
export function normalizeDataRange(
    data: number[],
    min?: number,
    max?: number
): number[] {
    if (data.length === 0) return [];

    const lo = min ?? Math.min(...data);
    const hi = max ?? Math.max(...data);
    const range = hi - lo;

    if (range === 0) return data.map(() => 50);

    return data.map(v => ((v - lo) / range) * 100);
}

// ─── Colour Palette ──────────────────────────────────────────────────────────

/**
 * Generate `count` evenly-spaced HSL colours suitable for chart series.
 *
 * Returns CSS `hsl()` strings.
 */
export function generateChartColors(count: number): string[] {
    const colors: string[] = [];
    const saturation = 65;
    const lightness = 55;

    for (let i = 0; i < count; i++) {
        const hue = Math.round((360 / count) * i);
        colors.push(`hsl(${hue}, ${saturation}%, ${lightness}%)`);
    }

    return colors;
}
