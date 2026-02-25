import { TeamConfig } from '../models/Team';
import { apiClient } from '../api/apiClient';
import { extractHttpErrorMessage, isRaiError, isSearchValidationError } from '../utils/errorUtils';

export class TeamService {
    /**
     * Upload a custom team configuration
     */
    private static readonly STORAGE_KEY = 'macae.v4.customTeam';

    static storageTeam(team: TeamConfig): boolean {
        // Persist a TeamConfig to localStorage (browser-only).
        if (typeof window === 'undefined' || !window.localStorage) return false;
        try {
            const serialized = JSON.stringify(team);
            window.localStorage.setItem(TeamService.STORAGE_KEY, serialized);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Initialize user's team with default HR team configuration
     * This calls the backend /init_team endpoint which sets up the default team
     */
    static async initializeTeam(team_switched: boolean = false): Promise<{
        success: boolean;
        data?: {
            status: string;
            team_id?: string;
            team?: any;
            requires_team_upload?: boolean;
        };
        error?: string;
    }> {
        try {
            const response = await apiClient.get('/v4/init_team', {
                params: {
                    team_switched
                }
            });

            return {
                success: true,
                data: response
            };
        } catch (error: any) {
            return {
                success: false,
                error: extractHttpErrorMessage(error, 'Failed to initialize team')
            };
        }
    }

    static getStoredTeam(): TeamConfig | null {
        if (typeof window === 'undefined' || !window.localStorage) return null;
        try {
            const raw = window.localStorage.getItem(TeamService.STORAGE_KEY);
            if (!raw) return null;
            const parsed = JSON.parse(raw);
            return parsed as TeamConfig;
        } catch {
            return null;
        }
    }

    static async uploadCustomTeam(teamFile: File): Promise<{
        modelError?: any; success: boolean; team?: TeamConfig; error?: string; raiError?: any; searchError?: any
    }> {
        try {
            const formData = new FormData();
            formData.append('file', teamFile);
            const response = await apiClient.upload('/v4/upload_team_config', formData);

            return {
                success: true,
                team: response.team
            };
        } catch (error: any) {
            const errorMessage = extractHttpErrorMessage(error, 'Failed to upload team configuration');

            if (isRaiError(errorMessage)) {
                return {
                    success: false,
                    raiError: {
                        error_type: 'RAI_VALIDATION_FAILED',
                        message: errorMessage,
                        description: errorMessage
                    }
                };
            }

            if (isSearchValidationError(errorMessage)) {
                return {
                    success: false,
                    searchError: {
                        error_type: 'SEARCH_VALIDATION_FAILED',
                        message: errorMessage,
                        description: errorMessage
                    }
                };
            }

            return {
                success: false,
                error: errorMessage
            };
        }
    }

    /**
     * Get user's custom teams
     */
    static async getUserTeams(): Promise<TeamConfig[]> {
        try {
            const response = await apiClient.get('/v4/team_configs');

            // The apiClient returns the response data directly, not wrapped in a data property
            const teams = Array.isArray(response) ? response : [];

            return teams;
        } catch (error: any) {
            return [];
        }
    }

    /**
     * Get a specific team by ID
     */
    static async getTeamById(teamId: string): Promise<TeamConfig | null> {
        try {
            const teams = await this.getUserTeams();
            const team = teams.find(t => t.team_id === teamId);
            return team || null;
        } catch (error: any) {
            return null;
        }
    }

    /**
     * Delete a custom team
     */
    static async deleteTeam(teamId: string): Promise<boolean> {
        try {
            await apiClient.delete(`/v4/team_configs/${teamId}`);
            return true;
        } catch (error: any) {
            return false;
        }
    }

    /**
     * Select a team for a plan/session
     */
    static async selectTeam(teamId: string): Promise<{
        success: boolean;
        data?: any;
        error?: string;
    }> {
        try {
            const response = await apiClient.post('/v4/select_team', {
                team_id: teamId,
            });

            return {
                success: true,
                data: response
            };
        } catch (error: any) {
            return {
                success: false,
                error: extractHttpErrorMessage(error, 'Failed to select team')
            };
        }
    }

    /**
     * Validate a team configuration JSON structure
     */
    static validateTeamConfig(config: any): { isValid: boolean; errors: string[]; warnings: string[] } {
        const errors: string[] = [];
        const warnings: string[] = [];

        // Required fields validation
        const requiredFields = ['id', 'team_id', 'name', 'description', 'status', 'created', 'created_by', 'agents'];
        for (const field of requiredFields) {
            if (!config[field]) {
                errors.push(`Missing required field: ${field}`);
            }
        }

        // Status validation
        if (config.status && !['visible', 'hidden'].includes(config.status)) {
            errors.push('Status must be either "visible" or "hidden"');
        }

        // Agents validation
        if (config.agents && Array.isArray(config.agents)) {
            config.agents.forEach((agent: any, index: number) => {
                const agentRequiredFields = ['input_key', 'type', 'name'];
                for (const field of agentRequiredFields) {
                    if (!agent[field]) {
                        errors.push(`Agent ${index + 1}: Missing required field: ${field}`);
                    }
                }

                const isProxyAgent = agent.name && agent.name.toLowerCase() === 'proxyagent';

                // Deployment name validation (skip for proxy agents)
                if (!isProxyAgent && !agent.deployment_name) {
                    errors.push(`Agent ${index + 1} (${agent.name}): Missing required field: deployment_name (required for non-proxy agents)`);
                }


                // RAG agent validation
                if (agent.use_rag === true && !agent.index_name) {
                    errors.push(`Agent ${index + 1} (${agent.name}): RAG agents must have an index_name`);
                }

                // New field warnings for completeness
                if (agent.type === 'RAG' && !agent.use_rag) {
                    warnings.push(`Agent ${index + 1} (${agent.name}): RAG type agent should have use_rag: true`);
                }

                if (agent.use_rag && !agent.index_endpoint) {
                    warnings.push(`Agent ${index + 1} (${agent.name}): RAG agent missing index_endpoint (will use default)`);
                }
            });
        } else if (config.agents) {
            errors.push('Agents must be an array');
        }

        // Starting tasks validation
        if (config.starting_tasks && Array.isArray(config.starting_tasks)) {
            config.starting_tasks.forEach((task: any, index: number) => {
                const taskRequiredFields = ['id', 'name', 'prompt'];
                for (const field of taskRequiredFields) {
                    if (!task[field]) {
                        warnings.push(`Starting task ${index + 1}: Missing recommended field: ${field}`);
                    }
                }
            });
        }

        // Optional field checks
        const optionalFields = ['logo', 'plan', 'protected'];
        for (const field of optionalFields) {
            if (!config[field]) {
                warnings.push(`Optional field missing: ${field} (recommended for better user experience)`);
            }
        }

        return { isValid: errors.length === 0, errors, warnings };
    }
}

export default TeamService;
