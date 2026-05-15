export interface Agent {
    input_key: string;
    type: string;
    name: string;
    system_message?: string;
    description?: string;
    icon?: string;
    index_name?: string;
    index_endpoint?: string;  // New: For RAG agents with custom endpoints
    deployment_name?: string;
    id?: string;
    capabilities?: string[];
    role?: string;
    use_rag?: boolean;        // New: Flag for RAG capabilities
    use_mcp?: boolean;        // New: Flag for MCP (Model Context Protocol)
    coding_tools?: boolean;   // New: Flag for coding capabilities
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
