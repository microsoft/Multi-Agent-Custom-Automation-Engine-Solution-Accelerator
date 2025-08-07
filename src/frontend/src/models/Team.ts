export interface Agent {
    id: string;
    name: string;
    description: string;
    capabilities?: string[];
    role?: string;
}

export interface StartingTask {
    id: string;
    name: string;
    prompt: string;
    created: string;
    creator: string;
    logo: string;
}

export interface Team {
    id: string;
    name: string;
    description: string;
    agents: Agent[];
    teamType: 'default' | 'custom';
    logoUrl?: string;
    category?: string;
}

// Backend-compatible Team model
export interface TeamConfig {
    team_id: string;
    name: string;
    description: string;
    status: string;
    created: string;
    created_by: string;
    logo: string;
    plan: string;
    agents: Agent[];
    starting_tasks: (string | StartingTask)[];
}

export interface TeamUploadResponse {
    success: boolean;
    teamId?: string;
    message?: string;
    errors?: string[];
}
