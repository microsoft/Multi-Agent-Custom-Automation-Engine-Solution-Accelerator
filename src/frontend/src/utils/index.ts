/**
 * Utils barrel — re-exports all domain-specific utility modules.
 *
 * Prefer importing from the specific module (e.g. `@/utils/httpUtils`)
 * when only a few symbols are needed, to keep bundle tree-shaking optimal.
 */

// HTTP production utilities
export {
    retryRequest,
    throttle,
    debounce,
} from './httpUtils';
export type {
    RetryOptions,
    ThrottledFn,
    DebouncedFn,
} from './httpUtils';

// API-level caching & deduplication
export { RequestCache, RequestTracker } from './apiUtils';

// JSON / Python-repr parsing
export {
    parseJsonSafe,
    unescapeReprString,
    cleanActionText,
    extractReprField,
    tryParseJsonOrPassthrough,
} from './jsonUtils';

// Message & text formatting
export {
    cleanTextToSpaces,
    cleanHRAgentText,
    formatDate,
    createAgentMessage,
} from './messageUtils';

// Error handling utilities
export {
    extractHttpErrorMessage,
    isRaiError,
    isSearchValidationError,
    formatErrorMessage,
    extractNestedContent,
} from './errorUtils';

// Chart utilities
export {
    formatChartValue,
    normalizeDataRange,
    generateChartColors,
} from './chartUtils';

// Agent icon utilities (existing)
export {
    getAgentIcon,
    getAgentDisplayName,
    getAgentDisplayNameWithSuffix,
} from './agentIconUtils';
