/**
 * Enumerations used throughout the application
 */

/**
 * Enumeration of agent types.
 * This includes common/default agent types, but the system supports dynamic agent types from JSON uploads.
 */
export enum AgentType {
    // Legacy/System agent types
    HUMAN = "Human_Agent",
    HR = "Hr_Agent",
    MARKETING = "Marketing_Agent",
    PROCUREMENT = "Procurement_Agent",
    PRODUCT = "Product_Agent",
    GENERIC = "Generic_Agent",
    TECH_SUPPORT = "Tech_Support_Agent",
    GROUP_CHAT_MANAGER = "Group_Chat_Manager",
    PLANNER = "Planner_Agent",

    // Common uploadable agent types
    MAGENTIC_ONE = "MagenticOne",
    CUSTOM = "Custom",
    RAG = "RAG",

    // Specific agent names (can be any name with any type)
    CODER = "Coder",
    EXECUTOR = "Executor",
    FILE_SURFER = "FileSurfer",
    WEB_SURFER = "WebSurfer",
    SENSOR_SENTINEL = "SensorSentinel",
    MAINTENANCE_KB_AGENT = "MaintanceKBAgent",
}


/**
 * Utility functions for working with agent types
 */
export class AgentTypeUtils {
    /**
     * Get display name for an agent type
     */
    static getDisplayName(agentType: AgentType): string {
        // Convert to string first
        const typeStr = String(agentType);

        // Handle specific formatting for known patterns
        if (typeStr.includes('_Agent')) {
            return typeStr.replace('_Agent', '').replace('_', ' ');
        }

        // Handle camelCase and PascalCase names
        return typeStr.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase()).trim();
    }

    /**
     * Check if an agent type is a known/default type
     */
    static isKnownType(agentType: AgentType): boolean {
        return Object.values(AgentType).includes(agentType);
    }

    /**
     * Get agent type from string, with fallback to the original string
     */
    static fromString(type: string): AgentType {
        // First check if it's a known enum value
        const enumValue = Object.values(AgentType).find(value => value === type);
        if (enumValue) {
            return enumValue;
        }

        // Return the custom type as-is
        return AgentType.CUSTOM;
    }

    /**
     * Get agent type category
     */
    static getAgentCategory(agentType: AgentType): 'system' | 'magentic-one' | 'custom' | 'rag' | 'unknown' {
        const typeStr = String(agentType);

        // System/Legacy agents
        if ([
            'Human_Agent', 'Hr_Agent', 'Marketing_Agent', 'Procurement_Agent',
            'Product_Agent', 'Generic_Agent', 'Tech_Support_Agent',
            'Group_Chat_Manager', 'Planner_Agent'
        ].includes(typeStr)) {
            return 'system';
        }

        // MagenticOne framework agents
        if (typeStr === 'MagenticOne' || [
            'Coder', 'Executor', 'FileSurfer', 'WebSurfer'
        ].includes(typeStr)) {
            return 'magentic-one';
        }

        // RAG agents
        if (typeStr === 'RAG' || typeStr.toLowerCase().includes('rag') || typeStr.toLowerCase().includes('kb')) {
            return 'rag';
        }

        // Custom agents
        if (typeStr === 'Custom') {
            return 'custom';
        }

        return 'unknown';
    }

    /**
     * Get icon for agent type based on category and name
     */
    static getAgentIcon(agentType: AgentType, providedIcon?: string): string {
        // If icon is explicitly provided, use it
        if (providedIcon && providedIcon.trim()) {
            return providedIcon;
        }

        const category = this.getAgentCategory(agentType);
        const typeStr = String(agentType);

        // Specific agent name mappings
        const iconMap: Record<string, string> = {
            'Coder': 'Terminal',
            'Executor': 'MonitorCog',
            'FileSurfer': 'File',
            'WebSurfer': 'Globe',
            'SensorSentinel': 'BookMarked',
            'MaintanceKBAgent': 'Search',
        };

        if (iconMap[typeStr]) {
            return iconMap[typeStr];
        }

        // Category-based defaults
        switch (category) {
            case 'system':
                return 'Person';
            case 'magentic-one':
                return 'BrainCircuit';
            case 'rag':
                return 'Search';
            case 'custom':
                return 'Wrench';
            default:
                return 'Robot';
        }
    }

    /**
     * Validate agent configuration
     */
    static validateAgent(agent: any): { isValid: boolean; errors: string[] } {
        const errors: string[] = [];

        if (!agent || typeof agent !== 'object') {
            errors.push('Agent must be a valid object');
            return { isValid: false, errors };
        }

        // Required fields
        if (!agent.input_key || typeof agent.input_key !== 'string' || agent.input_key.trim() === '') {
            errors.push('Agent input_key is required and cannot be empty');
        }

        if (!agent.type || typeof agent.type !== 'string' || agent.type.trim() === '') {
            errors.push('Agent type is required and cannot be empty');
        }

        if (!agent.name || typeof agent.name !== 'string' || agent.name.trim() === '') {
            errors.push('Agent name is required and cannot be empty');
        }

        // Optional fields validation
        const optionalStringFields = ['system_message', 'description', 'icon', 'index_name'];
        optionalStringFields.forEach(field => {
            if (agent[field] !== undefined && typeof agent[field] !== 'string') {
                errors.push(`Agent ${field} must be a string if provided`);
            }
        });

        // Special validation for RAG agents
        if (agent.type === 'RAG' && (!agent.index_name || agent.index_name.trim() === '')) {
            errors.push('RAG agents must have a valid index_name specified');
        }

        return { isValid: errors.length === 0, errors };
    }

    /**
     * Get all available agent types (both enum and common custom types)
     */
    static getAllAvailableTypes(): AgentType[] {
        return [
            ...Object.values(AgentType),
            // Add other common types that might come from JSON uploads
        ];
    }
}

export enum role {
    user = "user",
    assistant = "assistant"
}
/**
 * Enumeration of possible statuses for a step.
 */
export enum StepStatus {
    PLANNED = "planned",
    AWAITING_FEEDBACK = "awaiting_feedback",
    APPROVED = "approved",
    REJECTED = "rejected",
    ACTION_REQUESTED = "action_requested",
    COMPLETED = "completed",
    FAILED = "failed"
}

/**
 * Enumeration of possible statuses for a plan.
 */
export enum PlanStatus {
    IN_PROGRESS = "in_progress",
    COMPLETED = "completed",
    FAILED = "failed"
}

/**
 * Enumeration of human feedback statuses.
 */
export enum HumanFeedbackStatus {
    REQUESTED = "requested",
    ACCEPTED = "accepted",
    REJECTED = "rejected"
}
