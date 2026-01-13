/**
 * Formats a date according to the provided format string.
 * Supported tokens:
 *  - YYYY: 4-digit year
 *  - YY: 2-digit year
 *  - MMM: short month name (e.g., Jan)
 *  - MM: 2-digit month
 *  - M: 1 or 2-digit month
 *  - DD: 2-digit day
 *  - D: 1 or 2-digit day
 *  - HH: 2-digit hour (24h)
 *  - H: 1 or 2-digit hour (24h)
 *  - hh: 2-digit hour (12h)
 *  - h: 1 or 2-digit hour (12h)
 *  - mm: 2-digit minute
 *  - m: 1 or 2-digit minute
 *  - A: AM/PM
 *
 * @param date Date | string | number
 * @param format string
 * @returns string
 */
export const formatDate = (
    date: Date | string | number,
    format?: string
): string => {
    const d = date instanceof Date ? date : new Date(date);

    if (isNaN(d.getTime())) return '';

    if (!format) {
        // Use system's locale date and time format
        return d.toLocaleString();
    }

    const monthsShort = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];

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
        .sort(([a], [b]) => b.length - a.length)
        .forEach(([token, value]) => {
            formatted = formatted.replace(new RegExp(token, 'g'), value);
        });

    return formatted;
}