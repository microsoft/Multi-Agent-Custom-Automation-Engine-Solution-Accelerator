import React from 'react';
import {
    Desktop20Regular,
    Code20Regular,
    Building20Regular,
    Organization20Regular,
    Search20Regular,
    Globe20Regular,
    Database20Regular,
    Wrench20Regular,
    DocumentData20Regular,
    ChartMultiple20Regular,
    Bot20Regular,
    DataUsage20Regular,
    TableSimple20Regular,
    DataTrending20Regular,  // Replace Analytics20Regular with DataTrending20Regular
    Settings20Regular,
    Brain20Regular,
    Target20Regular,
    Flash20Regular,
    Shield20Regular
} from '@fluentui/react-icons';
import { TeamService } from '@/services/TeamService';
import { TaskService } from '@/services';
import { iconMap } from '@/models/homeInput';

// Extended icon mapping for user-uploaded string icons
const fluentIconMap: Record<string, React.ComponentType<any>> = {
    'Desktop20Regular': Desktop20Regular,
    'Code20Regular': Code20Regular,
    'Building20Regular': Building20Regular,
    'Organization20Regular': Organization20Regular,
    'Search20Regular': Search20Regular,
    'Globe20Regular': Globe20Regular,
    'Database20Regular': Database20Regular,
    'Wrench20Regular': Wrench20Regular,
    'DocumentData20Regular': DocumentData20Regular,
    'ChartMultiple20Regular': ChartMultiple20Regular,
    'Bot20Regular': Bot20Regular,
    'DataUsage20Regular': DataUsage20Regular,
    'TableSimple20Regular': TableSimple20Regular,
    'DataTrending20Regular': DataTrending20Regular,  // Updated
    'Analytics20Regular': DataTrending20Regular,     // Keep Analytics as alias
    'Settings20Regular': Settings20Regular,
    'Brain20Regular': Brain20Regular,
    'Target20Regular': Target20Regular,
    'Flash20Regular': Flash20Regular,
    'Shield20Regular': Shield20Regular,
    // Add common variations and aliases
    'desktop': Desktop20Regular,
    'code': Code20Regular,
    'building': Building20Regular,
    'organization': Organization20Regular,
    'search': Search20Regular,
    'globe': Globe20Regular,
    'database': Database20Regular,
    'wrench': Wrench20Regular,
    'document': DocumentData20Regular,
    'chart': ChartMultiple20Regular,
    'bot': Bot20Regular,
    'data': DataUsage20Regular,
    'table': TableSimple20Regular,
    'analytics': DataTrending20Regular,
    'trending': DataTrending20Regular,
    'settings': Settings20Regular,
    'brain': Brain20Regular,
    'target': Target20Regular,
    'flash': Flash20Regular,
    'shield': Shield20Regular
};

// Icon pool for unique assignment (excluding Person20Regular)
const AGENT_ICON_POOL = [
    Bot20Regular,
    DataTrending20Regular,  // Updated
    TableSimple20Regular,
    ChartMultiple20Regular,
    DataUsage20Regular,
    DocumentData20Regular,
    Settings20Regular,
    Brain20Regular,
    Target20Regular,
    Flash20Regular,
    Shield20Regular,
    Code20Regular,
    Search20Regular,
    Globe20Regular,
    Building20Regular,
    Organization20Regular,
    Wrench20Regular,
    Database20Regular,
    Desktop20Regular
];

// Cache for agent icon assignments to ensure consistency
const agentIconAssignments: Record<string, React.ComponentType<any>> = {};

/**
 * Generate a consistent hash from a string for icon assignment
 */
const generateHash = (str: string): number => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash);
};

/**
 * Match user-uploaded string icon to Fluent UI component
 */
const matchStringToFluentIcon = (iconString: string): React.ComponentType<any> | null => {
    if (!iconString || typeof iconString !== 'string') return null;

    // Try exact match first
    if (fluentIconMap[iconString]) {
        return fluentIconMap[iconString];
    }

    // Try case-insensitive match
    const lowerIconString = iconString.toLowerCase();
    if (fluentIconMap[lowerIconString]) {
        return fluentIconMap[lowerIconString];
    }

    // Try removing common suffixes and prefixes
    const cleanedIconString = iconString
        .replace(/20Regular$/i, '')
        .replace(/Regular$/i, '')
        .replace(/20$/i, '')
        .replace(/^fluent/i, '')
        .replace(/^icon/i, '')
        .toLowerCase()
        .trim();

    if (fluentIconMap[cleanedIconString]) {
        return fluentIconMap[cleanedIconString];
    }

    return null;
};

/**
 * Get deterministic icon for agent based on name pattern matching
 * This ensures agents with the same name always get the same icon
 */
const getDeterministicAgentIcon = (cleanName: string): React.ComponentType<any> => {
    // Pattern-based assignment - deterministic based on agent name
    if (cleanName.includes('data') && cleanName.includes('order')) {
        return TableSimple20Regular;
    } else if (cleanName.includes('data') && cleanName.includes('customer')) {
        return DataUsage20Regular;
    } else if (cleanName.includes('analysis') || cleanName.includes('recommend') || cleanName.includes('insight')) {
        return DataTrending20Regular;
    } else if (cleanName.includes('proxy') || cleanName.includes('interface')) {
        return Bot20Regular;
    } else if (cleanName.includes('brain') || cleanName.includes('ai') || cleanName.includes('intelligence')) {
        return Brain20Regular;
    } else if (cleanName.includes('security') || cleanName.includes('protect') || cleanName.includes('guard')) {
        return Shield20Regular;
    } else if (cleanName.includes('target') || cleanName.includes('goal') || cleanName.includes('objective')) {
        return Target20Regular;
    } else if (cleanName.includes('fast') || cleanName.includes('quick') || cleanName.includes('speed')) {
        return Flash20Regular;
    } else if (cleanName.includes('code') || cleanName.includes('dev') || cleanName.includes('program')) {
        return Code20Regular;
    } else if (cleanName.includes('search') || cleanName.includes('find') || cleanName.includes('lookup')) {
        return Search20Regular;
    } else if (cleanName.includes('web') || cleanName.includes('internet') || cleanName.includes('online')) {
        return Globe20Regular;
    } else if (cleanName.includes('business') || cleanName.includes('company') || cleanName.includes('enterprise')) {
        return Building20Regular;
    } else if (cleanName.includes('hr') || cleanName.includes('human') || cleanName.includes('people')) {
        return Organization20Regular;
    } else if (cleanName.includes('tool') || cleanName.includes('utility') || cleanName.includes('helper')) {
        return Wrench20Regular;
    } else if (cleanName.includes('document') || cleanName.includes('file') || cleanName.includes('report')) {
        return DocumentData20Regular;
    } else if (cleanName.includes('config') || cleanName.includes('setting') || cleanName.includes('manage')) {
        return Settings20Regular;
    } else if (cleanName.includes('data') || cleanName.includes('database')) {
        return Database20Regular;
    } else {
        // Use hash-based assignment for consistent selection across identical names
        const hash = generateHash(cleanName);
        const iconIndex = hash % AGENT_ICON_POOL.length;
        return AGENT_ICON_POOL[iconIndex];
    }
};

/**
 * Get unique icon for an agent based on their name and context
 * Ensures agents with identical names get identical icons
 */
const getUniqueAgentIcon = (
    agentName: string,
    allAgentNames: string[],
    iconStyle: React.CSSProperties
): React.ReactNode => {
    const cleanName = TaskService.cleanTextToSpaces(agentName).toLowerCase();

    // If we already assigned an icon to this agent, use it
    if (agentIconAssignments[cleanName]) {
        const IconComponent = agentIconAssignments[cleanName];
        return React.createElement(IconComponent, { style: iconStyle });
    }

    // Get deterministic icon based on agent name patterns
    // This ensures same names always get the same icon regardless of assignment order
    const selectedIcon = getDeterministicAgentIcon(cleanName);

    // Cache the assignment for future lookups
    agentIconAssignments[cleanName] = selectedIcon;

    return React.createElement(selectedIcon, { style: iconStyle });
};

/**
 * Comprehensive utility function to get agent icon from multiple data sources
 * with consistent fallback patterns across all components
 */
export const getAgentIcon = (
    agentName: string,
    planData?: any,
    planApprovalRequest?: any,
    iconColor: string = 'var(--colorNeutralForeground2)'
): React.ReactNode => {
    const iconStyle = { fontSize: '16px', color: iconColor };

    // 1. First priority: Get from uploaded team configuration in planData
    if (planData?.team?.agents) {
        const cleanAgentName = TaskService.cleanTextToSpaces(agentName);

        const agent = planData.team.agents.find((a: any) =>
            TaskService.cleanTextToSpaces(a.name || '').toLowerCase().includes(cleanAgentName.toLowerCase()) ||
            TaskService.cleanTextToSpaces(a.type || '').toLowerCase().includes(cleanAgentName.toLowerCase()) ||
            TaskService.cleanTextToSpaces(a.input_key || '').toLowerCase().includes(cleanAgentName.toLowerCase())
        );

        if (agent?.icon) {
            // Try to match string to Fluent icon component first
            const FluentIconComponent = matchStringToFluentIcon(agent.icon);
            if (FluentIconComponent) {
                return React.createElement(FluentIconComponent, { style: iconStyle });
            }

            // Fallback: check if it's in the existing iconMap
            if (iconMap[agent.icon]) {
                return React.cloneElement(iconMap[agent.icon] as React.ReactElement, {
                    style: iconStyle
                });
            }
        }
    }

    // 2. Second priority: Get from stored team configuration (TeamService)
    const storedTeam = TeamService.getStoredTeam();
    if (storedTeam?.agents) {
        const cleanAgentName = TaskService.cleanTextToSpaces(agentName);

        const agent = storedTeam.agents.find(a =>
            TaskService.cleanTextToSpaces(a.name).toLowerCase().includes(cleanAgentName.toLowerCase()) ||
            a.type.toLowerCase().includes(cleanAgentName.toLowerCase()) ||
            a.input_key.toLowerCase().includes(cleanAgentName.toLowerCase())
        );

        if (agent?.icon && iconMap[agent.icon]) {
            return React.cloneElement(iconMap[agent.icon] as React.ReactElement, {
                style: iconStyle
            });
        }
    }

    // 3. Third priority: Get from participant_descriptions in planApprovalRequest
    if (planApprovalRequest?.context?.participant_descriptions) {
        const participantDesc = planApprovalRequest.context.participant_descriptions[agentName];
        if (participantDesc?.icon && iconMap[participantDesc.icon]) {
            return React.cloneElement(iconMap[participantDesc.icon] as React.ReactElement, {
                style: iconStyle
            });
        }
    }

    // 4. Deterministic icon assignment - ensures same names get same icons
    // Get all agent names from current context for unique assignment
    let allAgentNames: string[] = [];

    if (planApprovalRequest?.team) {
        allAgentNames = planApprovalRequest.team;
    } else if (planData?.team?.agents) {
        allAgentNames = planData.team.agents.map((a: any) => a.name || a.type || '');
    } else if (storedTeam?.agents) {
        allAgentNames = storedTeam.agents.map(a => a.name);
    }

    return getUniqueAgentIcon(agentName, allAgentNames, iconStyle);
};

/**
 * Clear agent icon assignments (useful when switching teams/contexts)
 */
export const clearAgentIconAssignments = (): void => {
    Object.keys(agentIconAssignments).forEach(key => {
        delete agentIconAssignments[key];
    });
};

/**
 * Get agent display name with proper formatting
 * Removes redundant "Agent" suffix and handles proper spacing
 */
export const getAgentDisplayName = (agentName: string): string => {
    if (!agentName) return 'Assistant';

    // Clean and format the name
    let cleanName = TaskService.cleanTextToSpaces(agentName);

    // Remove "Agent" suffix if it exists (case insensitive)
    cleanName = cleanName.replace(/\s*agent\s*$/gi, '').trim();

    // Convert to proper case
    cleanName = cleanName
        .replace(/\bHRHelper\b/gi, 'HR Helper')
        .replace(/\bHR([A-Z])/g, 'HR $1')        // Add space after HR before capital letter
        .replace(/\bIT([A-Z])/g, 'IT $1')        // Add space after IT before capital letter
        .replace(/\bAPI([A-Z])/g, 'API $1');     // Add space after API before capital letter

    // Convert to proper case
    cleanName = cleanName.replace(/\b\w/g, l => l.toUpperCase());


    // Handle special cases for better readability
    cleanName = cleanName
        .replace(/\bKb\b/g, 'KB')          // KB instead of Kb
        .replace(/\bApi\b/g, 'API')        // API instead of Api
        .replace(/\bHr\b/g, 'HR')          // HR instead of Hr
        .replace(/\bIt\b/g, 'IT')          // IT instead of It
        .replace(/\bAi\b/g, 'AI')          // AI instead of Ai
        .replace(/\bUi\b/g, 'UI')          // UI instead of Ui
        .replace(/\bDb\b/g, 'DB');         // DB instead of Db

    return cleanName || 'Assistant';
};

/**
 * Get agent display name with "Agent" suffix for display purposes
 */
export const getAgentDisplayNameWithSuffix = (agentName: string): string => {
    const baseName = getAgentDisplayName(agentName);
    return `${baseName} Agent`;
};

/**
 * Get agent icon with custom styling override
 */
/**
 * Get agent icon with custom styling override
 */
export const getStyledAgentIcon = (
    agentName: string,
    customStyle: React.CSSProperties,
    planData?: any,
    planApprovalRequest?: any
): React.ReactNode => {
    const icon = getAgentIcon(agentName, planData, planApprovalRequest);

    if (React.isValidElement(icon)) {
        try {
            // Safely merge styles
            const mergedStyle = {
                ...(icon.props as any)?.style,
                ...customStyle
            };

            return React.cloneElement(icon as React.ReactElement<any>, {
                style: mergedStyle
            });
        } catch (error) {
            // Fallback: return original icon if cloning fails
            console.warn('Failed to apply custom style to agent icon:', error);
            return icon;
        }
    }

    return icon;
};