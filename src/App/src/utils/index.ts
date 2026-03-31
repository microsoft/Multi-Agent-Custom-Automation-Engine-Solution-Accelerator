/**
 * Utils barrel export
 *
 * Domain-based organization:
 *  - utils        → date formatting helpers
 *  - errorUtils   → user-friendly error messages & styles
 *  - messageUtils → message formatting / truncation
 *  - agentIconUtils → agent-to-icon mapping
 */

export { formatDate } from './utils';
export { getErrorMessage, getErrorStyle } from './errorUtils';
export { formatErrorMessage, extractPlainAnswer, truncate } from './messageUtils';
export {
    getAgentIcon,
    clearAgentIconAssignments,
    getAgentDisplayName,
    getAgentDisplayNameWithSuffix,
    getStyledAgentIcon,
} from './agentIconUtils';
