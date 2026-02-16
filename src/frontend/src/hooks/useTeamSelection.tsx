import { useState, useCallback } from 'react';
import { TeamConfig } from '../models/Team';
import { TeamService } from '../services/TeamService';

interface UseTeamSelectionProps {
  sessionId?: string;
  onTeamSelected?: (team: TeamConfig, result: any) => void;
  onError?: (error: string) => void;
}

interface UseTeamSelectionReturn {
  selectedTeam: TeamConfig | null;
  isLoading: boolean;
  error: string | null;
  selectTeam: (team: TeamConfig) => Promise<boolean>;
  clearSelection: () => void;
  clearError: () => void;
}

/**
 * React hook for managing team selection with backend integration
 */
export const useTeamSelection = ({
  sessionId,
  onTeamSelected,
  onError,
}: UseTeamSelectionProps = {}): UseTeamSelectionReturn => {
  const [selectedTeam, setSelectedTeam] = useState<TeamConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectTeam = useCallback(async (team: TeamConfig): Promise<boolean> => {
    if (isLoading) return false;

    setIsLoading(true);
    setError(null);

    try {
      console.log('Selecting team:', team.name, 'with session ID:', sessionId);

      const result = await TeamService.selectTeam(team.team_id);

      if (result.success) {
        setSelectedTeam(team);
        console.log('Team selection successful:', result.data);

        // Call success callback
        onTeamSelected?.(team, result.data);

        return true;
      } else {
        const errorMessage = result.error || 'Failed to select team';
        setError(errorMessage);

        // Call error callback
        onError?.(errorMessage);

        return false;
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to select team';
      setError(errorMessage);

      console.error('Team selection error:', err);

      // Call error callback
      onError?.(errorMessage);

      return false;
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, sessionId, onTeamSelected, onError]);

  const clearSelection = useCallback(() => {
    setSelectedTeam(null);
    setError(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    selectedTeam,
    isLoading,
    error,
    selectTeam,
    clearSelection,
    clearError,
  };
};

export default useTeamSelection;
