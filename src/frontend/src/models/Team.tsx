export interface Agent {
    input_key: string;
    type: string;
    name: string;
    system_message?: string;
    description?: string;
    icon?: string;
    index_name?: string;
    deployment_name?:string;
    id?: string;
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

// Backend-compatible Team model that matches uploaded JSON structure
export interface TeamConfig {
    id: string;
    team_id: string;
    name: string;
    description: string;
    status: 'visible' | 'hidden';
    protected?: boolean;
    created: string;
    created_by: string;
    logo: string;
    plan: string;
    agents: Agent[];
    starting_tasks: StartingTask[];
}

export interface TeamUploadResponse {
    success: boolean;
    teamId?: string;
    message?: string;
    errors?: string[];
}
