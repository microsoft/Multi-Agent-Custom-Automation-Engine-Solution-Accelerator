import { TeamConfig } from '../models/Team';
import { apiClient } from '../api/apiClient';

export class TeamService {
    /**
     * Upload a custom team configuration
     */
    static async uploadCustomTeam(teamFile: File): Promise<{
        modelError?: any; success: boolean; team?: TeamConfig; error?: string; raiError?: any; searchError?: any
    }> {
        try {
            const formData = new FormData();
            formData.append('file', teamFile);

            const response = await apiClient.upload('/upload_team_config', formData);

            return {
                success: true,
                team: response.data
            };
        } catch (error: any) {

            // Check if this is an RAI validation error
            const errorDetail = error.response?.data?.detail || error.response?.data;

            // If the error message contains "inappropriate content", treat it as RAI error
            if (typeof errorDetail === 'string' && errorDetail.includes('inappropriate content')) {
                return {
                    success: false,
                    raiError: {
                        error_type: 'RAI_VALIDATION_FAILED',
                        message: errorDetail,
                        description: errorDetail
                    }
                };
            }

            // If the error message contains "Search index validation failed", treat it as search error
            if (typeof errorDetail === 'string' && errorDetail.includes('Search index validation failed')) {
                return {
                    success: false,
                    searchError: {
                        error_type: 'SEARCH_VALIDATION_FAILED',
                        message: errorDetail,
                        description: errorDetail
                    }
                };
            }

            // Get error message from the response
            let errorMessage = error.message || 'Failed to upload team configuration';
            if (error.response?.data?.detail) {
                errorMessage = error.response.data.detail;
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
            const response = await apiClient.get('/v3/team_configs');

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
            const response = await apiClient.delete(`/v3/team_configs/${teamId}`);
            return true;
        } catch (error: any) {
            return false;
        }
    }
}

export default TeamService;
