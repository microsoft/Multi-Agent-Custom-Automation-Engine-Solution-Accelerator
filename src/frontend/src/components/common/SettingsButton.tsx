import React, { useState } from 'react';
import {
  Button,
  Dialog,
  DialogTrigger,
  DialogSurface,
  DialogTitle,
  DialogContent,
  DialogBody,
  DialogActions,
  Text,
  Spinner,
  Card,
  Body1,
  Body2,
  Caption1,
  Tooltip,
  Badge,
  Input,
} from '@fluentui/react-components';
import {
  Settings20Regular,
  CloudAdd20Regular,
  Delete20Regular,
  Checkmark20Filled,
  Search20Regular,
  Desktop20Regular,
  BookmarkMultiple20Regular,
  Person20Regular,
  Building20Regular,
  Document20Regular,
  Database20Regular,
  Play20Regular,
  Shield20Regular,
  Globe20Regular,
  Clipboard20Regular,
  WindowConsole20Regular,
  Code20Regular,
  Wrench20Regular,
} from '@fluentui/react-icons';
import { TeamConfig } from '../../models/Team';
import { TeamService } from '../../services/TeamService';

import '../../index.css'

// Icon mapping function to convert string icons to FluentUI icons
const getIconFromString = (iconString: string): React.ReactNode => {
  const iconMap: Record<string, React.ReactNode> = {
    // Agent icons
    'Terminal': <WindowConsole20Regular />,
    'MonitorCog': <Desktop20Regular />,
    'BookMarked': <BookmarkMultiple20Regular />,
    'Search': <Search20Regular />,
    'Robot': <Person20Regular />, // Fallback since Robot20Regular doesn't exist
    'Code': <Code20Regular />,
    'Play': <Play20Regular />,
    'Shield': <Shield20Regular />,
    'Globe': <Globe20Regular />,
    'Person': <Person20Regular />,
    'Database': <Database20Regular />,
    'Document': <Document20Regular />,
    
    // Team logos
    'Wrench': <Wrench20Regular />,
    'TestTube': <Clipboard20Regular />, // Fallback since TestTube20Regular doesn't exist
    'Building': <Building20Regular />,
    'Desktop': <Desktop20Regular />,
    
    // Common fallbacks
    'default': <Person20Regular />,
  };
  
  return iconMap[iconString] || iconMap['default'] || <Person20Regular />;
};

interface SettingsButtonProps {
  onTeamSelect?: (team: TeamConfig | null) => void;
  onTeamUpload?: () => Promise<void>;
  selectedTeam?: TeamConfig | null;
}

const SettingsButton: React.FC<SettingsButtonProps> = ({
  onTeamSelect,
  onTeamUpload,
  selectedTeam,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [teams, setTeams] = useState<TeamConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [tempSelectedTeam, setTempSelectedTeam] = useState<TeamConfig | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [teamToDelete, setTeamToDelete] = useState<TeamConfig | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const loadTeams = async () => {
    setLoading(true);
    setError(null);
    try {
      // Get all teams from the API (no separation between default and user teams)
      const teamsData = await TeamService.getUserTeams();
      setTeams(teamsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load teams');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenChange = async (open: boolean) => {
    setIsOpen(open);
    if (open) {
      await loadTeams();
      setTempSelectedTeam(selectedTeam || null);
      setError(null);
      setUploadMessage(null);
      setSearchQuery(''); // Clear search when opening
    } else {
      setTempSelectedTeam(null);
      setError(null);
      setUploadMessage(null);
      setSearchQuery(''); // Clear search when closing
    }
  };

  const handleContinue = () => {
    if (tempSelectedTeam) {
      onTeamSelect?.(tempSelectedTeam);
    }
    setIsOpen(false);
  };

  const handleCancel = () => {
    setTempSelectedTeam(null);
    setIsOpen(false);
  };

  // Filter teams based on search query
  const filteredTeams = teams.filter(team => 
    team.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    team.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Validation function for team configuration JSON
  const validateTeamConfig = (data: any): { isValid: boolean; errors: string[] } => {
    const errors: string[] = [];

    // Check if data is empty or null
    if (!data || typeof data !== 'object') {
      errors.push('JSON file cannot be empty and must contain a valid object');
      return { isValid: false, errors };
    }

    // Required root level fields
    if (!data.name || typeof data.name !== 'string' || data.name.trim() === '') {
      errors.push('Team name is required and cannot be empty');
    }

    if (!data.description || typeof data.description !== 'string' || data.description.trim() === '') {
      errors.push('Team description is required and cannot be empty');
    }

    // Additional required fields with defaults
    if (!data.status || typeof data.status !== 'string' || data.status.trim() === '') {
      errors.push('Team status is required and cannot be empty');
    }

    // Note: created and created_by are generated by the backend, so don't validate them here

    // Agents validation
    if (!data.agents || !Array.isArray(data.agents)) {
      errors.push('Agents array is required');
    } else if (data.agents.length === 0) {
      errors.push('Team must have at least one agent');
    } else {
      // Validate each agent
      data.agents.forEach((agent: any, index: number) => {
        if (!agent || typeof agent !== 'object') {
          errors.push(`Agent ${index + 1}: Invalid agent object`);
          return;
        }

        if (!agent.name || typeof agent.name !== 'string' || agent.name.trim() === '') {
          errors.push(`Agent ${index + 1}: Agent name is required and cannot be empty`);
        }

        if (!agent.type || typeof agent.type !== 'string' || agent.type.trim() === '') {
          errors.push(`Agent ${index + 1}: Agent type is required and cannot be empty`);
        }

        if (!agent.input_key || typeof agent.input_key !== 'string' || agent.input_key.trim() === '') {
          errors.push(`Agent ${index + 1}: Agent input_key is required and cannot be empty`);
        }

        // deployment_name is required for all agents (for model validation)
        if (!agent.deployment_name || typeof agent.deployment_name !== 'string' || agent.deployment_name.trim() === '') {
          errors.push(`Agent ${index + 1}: Agent deployment_name is required and cannot be empty`);
        }

        // index_name is required only for RAG agents (for search validation)
        if (agent.type && agent.type.toLowerCase() === 'rag') {
          if (!agent.index_name || typeof agent.index_name !== 'string' || agent.index_name.trim() === '') {
            errors.push(`Agent ${index + 1}: Agent index_name is required for RAG agents and cannot be empty`);
          }
        }

        // Optional fields validation (can be empty but must be strings if present)
        if (agent.description !== undefined && typeof agent.description !== 'string') {
          errors.push(`Agent ${index + 1}: Agent description must be a string`);
        }

        if (agent.system_message !== undefined && typeof agent.system_message !== 'string') {
          errors.push(`Agent ${index + 1}: Agent system_message must be a string`);
        }

        if (agent.icon !== undefined && typeof agent.icon !== 'string') {
          errors.push(`Agent ${index + 1}: Agent icon must be a string`);
        }

        // index_name is only validated for non-RAG agents here (RAG agents are validated above)
        if (agent.type && agent.type.toLowerCase() !== 'rag' && agent.index_name !== undefined && typeof agent.index_name !== 'string') {
          errors.push(`Agent ${index + 1}: Agent index_name must be a string`);
        }
      });
    }

    // Starting tasks validation (optional but must be valid if present)
    if (data.starting_tasks !== undefined) {
      if (!Array.isArray(data.starting_tasks)) {
        errors.push('Starting tasks must be an array if provided');
      } else {
        data.starting_tasks.forEach((task: any, index: number) => {
          if (!task || typeof task !== 'object') {
            errors.push(`Starting task ${index + 1}: Invalid task object`);
            return;
          }

          if (!task.name || typeof task.name !== 'string' || task.name.trim() === '') {
            errors.push(`Starting task ${index + 1}: Task name is required and cannot be empty`);
          }

          if (!task.prompt || typeof task.prompt !== 'string' || task.prompt.trim() === '') {
            errors.push(`Starting task ${index + 1}: Task prompt is required and cannot be empty`);
          }

          if (!task.id || typeof task.id !== 'string' || task.id.trim() === '') {
            errors.push(`Starting task ${index + 1}: Task id is required and cannot be empty`);
          }

          if (!task.created || typeof task.created !== 'string' || task.created.trim() === '') {
            errors.push(`Starting task ${index + 1}: Task created date is required and cannot be empty`);
          }

          if (!task.creator || typeof task.creator !== 'string' || task.creator.trim() === '') {
            errors.push(`Starting task ${index + 1}: Task creator is required and cannot be empty`);
          }

          if (task.logo !== undefined && typeof task.logo !== 'string') {
            errors.push(`Starting task ${index + 1}: Task logo must be a string if provided`);
          }
        });
      }
    }

    // Optional root level fields validation
    const stringFields = ['status', 'logo', 'plan'];
    stringFields.forEach(field => {
      if (data[field] !== undefined && typeof data[field] !== 'string') {
        errors.push(`${field} must be a string if provided`);
      }
    });

    if (data.protected !== undefined && typeof data.protected !== 'boolean') {
      errors.push('Protected field must be a boolean if provided');
    }

    return { isValid: errors.length === 0, errors };
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadLoading(true);
    setError(null);
    setUploadMessage('Reading and validating team configuration...');

    try {
      // First, validate the file type
      if (!file.name.toLowerCase().endsWith('.json')) {
        throw new Error('Please upload a valid JSON file');
      }

      // Read and parse the JSON file
      const fileContent = await file.text();
      let teamData;
      
      try {
        teamData = JSON.parse(fileContent);
      } catch (parseError) {
        throw new Error('Invalid JSON format. Please check your file syntax');
      }

      // Validate the team configuration
      setUploadMessage('Validating team configuration structure...');
      const validation = validateTeamConfig(teamData);
      
      if (!validation.isValid) {
        const errorMessage = `Team configuration validation failed:\n\n${validation.errors.map(error => `• ${error}`).join('\n')}`;
        throw new Error(errorMessage);
      }

      setUploadMessage('Uploading team configuration...');
      const result = await TeamService.uploadCustomTeam(file);
      
      if (result.success) {
        setUploadMessage('Team uploaded successfully!');
        
        // Add the new team to the existing list instead of full refresh
        if (result.team) {
          setTeams(currentTeams => [...currentTeams, result.team!]);
        }
        
        setUploadMessage(null);
        // Notify parent component about the upload
        if (onTeamUpload) {
          await onTeamUpload();
        }
      } else if (result.raiError) {
        setError('❌ Content Safety Check Failed\n\nYour team configuration contains content that doesn\'t meet our safety guidelines. Please review and modify:\n\n• Agent instructions and descriptions\n• Task prompts and content\n• Team descriptions\n\nEnsure all content is appropriate, helpful, and follows ethical AI principles.');
        setUploadMessage(null);
      } else if (result.modelError) {
        setError('🤖 Model Deployment Validation Failed\n\nYour team configuration references models that are not properly deployed:\n\n• Verify deployment_name values are correct\n• Ensure all models are deployed in Azure AI Foundry\n• Check model deployment names match exactly\n• Confirm access permissions to AI services\n\nAll agents require valid deployment_name for model access.');
        setUploadMessage(null);
      } else if (result.searchError) {
        setError('🔍 RAG Search Configuration Error\n\nYour team configuration includes RAG/search agents but has search index issues:\n\n• Verify search index names are correct\n• Ensure indexes exist in Azure AI Search\n• Check access permissions to search service\n• Confirm RAG agent configurations\n\nRAG agents require properly configured search indexes to function correctly.');
        setUploadMessage(null);
      } else {
        setError(result.error || 'Failed to upload team configuration');
        setUploadMessage(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to upload team configuration');
      setUploadMessage(null);
    } finally {
      setUploadLoading(false);
      // Reset the input
      event.target.value = '';
    }
  };

  const handleDeleteTeam = (team: TeamConfig, event: React.MouseEvent) => {
    event.stopPropagation();
    setTeamToDelete(team);
    setDeleteConfirmOpen(true);
  };

  const handleTeamSelect = (team: TeamConfig) => {
    setTempSelectedTeam(team);
    onTeamSelect?.(team);
  };

  const confirmDeleteTeam = async () => {
    if (!teamToDelete || deleteLoading) return;
    
    // Check if team is protected
    if (teamToDelete.protected) {
      setError('This team is protected and cannot be deleted.');
      setDeleteConfirmOpen(false);
      setTeamToDelete(null);
      return;
    }
    
    setDeleteLoading(true);
    
    try {
      // Attempt to delete the team
      const success = await TeamService.deleteTeam(teamToDelete.id);
      
      if (success) {
        // Close dialog and clear states immediately
        setDeleteConfirmOpen(false);
        setTeamToDelete(null);
        setDeleteLoading(false);
        
        // If the deleted team was currently selected, clear the selection
        if (tempSelectedTeam?.team_id === teamToDelete.team_id) {
          setTempSelectedTeam(null);
          // Also clear it from the parent component if it was the active selection
          if (selectedTeam?.team_id === teamToDelete.team_id) {
            onTeamSelect?.(null);
          }
        }
        
        // Update the teams list immediately by filtering out the deleted team
        setTeams(currentTeams => currentTeams.filter(team => team.id !== teamToDelete.id));
        
        // Then reload from server to ensure consistency
        await loadTeams();
        
      } else {
        setError('Failed to delete team configuration. The server rejected the deletion request.');
        setDeleteConfirmOpen(false);
        setTeamToDelete(null);
      }
    } catch (err: any) {
      
      // Provide more specific error messages based on the error type
      let errorMessage = 'Failed to delete team configuration. Please try again.';
      
      if (err.response?.status === 404) {
        errorMessage = 'Team not found. It may have already been deleted.';
      } else if (err.response?.status === 403) {
        errorMessage = 'You do not have permission to delete this team.';
      } else if (err.response?.status === 409) {
        errorMessage = 'Cannot delete team because it is currently in use.';
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message) {
        errorMessage = `Delete failed: ${err.message}`;
      }
      
      setError(errorMessage);
      setDeleteConfirmOpen(false);
      setTeamToDelete(null);
    } finally {
      setDeleteLoading(false);
    }
  };

  const renderTeamCard = (team: TeamConfig, isCustom = false) => {
    const isSelected = tempSelectedTeam?.team_id === team.team_id;
    
    return (
      <Card
        style={{
          border: isSelected ? '2px solid var(--colorBrandBackground)' : '1px solid var(--colorNeutralStroke1)',
          borderRadius: '8px',
          position: 'relative',
          transition: 'all 0.2s ease',
          backgroundColor: isSelected ? 'var(--colorBrandBackground2)' : 'var(--colorNeutralBackground1)',
          padding: '12px',
          width: '100%',
          boxSizing: 'border-box',
          display: 'block',
        }}
      >
        {/* Team Icon and Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <div style={{
            backgroundColor: 'var(--colorNeutralBackground3)',
            borderRadius: '4px',
            padding: '4px',
            width: '35px',
            height: '35px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <div style={{ fontSize: '20px', color: '#333' }}>
              {getIconFromString(team.logo)}
            </div>
          </div>
          
          <div style={{ flex: 1, minWidth: 0 }}>
            <Body1 style={{ 
              fontWeight: '600', 
              fontSize: '16px',
              margin: 0,
              color: 'var(--colorNeutralForeground1)'
            }}>
              {team.name}
            </Body1>
          </div>

          {/* Selection Checkmark */}
          {isSelected && (
            <div style={{
              backgroundColor: '#6264a7',
              borderRadius: '50%',
              width: '24px',
              height: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Checkmark20Filled style={{ color: 'white', fontSize: '14px' }} />
            </div>
          )}

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '8px' }}>
            {!isSelected && (
              <Tooltip content="Select this team" relationship="label">
                <Button
                  appearance="primary"
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTeamSelect(team);
                  }}
                >
                  Select
                </Button>
              </Tooltip>
            )}
            
            <Tooltip content="Delete team" relationship="label">
              <Button
                icon={<Delete20Regular />}
                appearance="subtle"
                size="small"
                onClick={(e) => handleDeleteTeam(team, e)}
                className="delete-team-button"
              />
            </Tooltip>
          </div>
        </div>

        {/* Description */}
        <div style={{ marginBottom: '12px' }}>
          <Caption1 style={{ color: '#666', fontSize: '14px', lineHeight: '1.4' }}>
            {team.description}
          </Caption1>
        </div>

        {/* Agents Section */}
        <div>
          <Body2 style={{ 
            fontWeight: '600', 
            marginBottom: '12px', 
            fontSize: '14px',
            color: '#333',
            display: 'block'
          }}>
            Agents
          </Body2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
            {team.agents.map((agent) => (
              <Badge
                key={agent.input_key}
                appearance="outline"
                style={{
                  backgroundColor: '#f8f9fa',
                  border: '1px solid #e1e1e1',
                  color: '#333',
                  fontSize: '12px',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <span style={{ fontSize: '14px', display: 'flex', alignItems: 'center' }}>
                  {getIconFromString(agent.icon || 'default')}
                </span>
                {agent.name}
              </Badge>
            ))}
          </div>
        </div>
      </Card>
    );
  };

  return (
    <>
    <Dialog open={isOpen} onOpenChange={(event, data) => handleOpenChange(data.open)}>
      <DialogTrigger disableButtonEnhancement>
        <Tooltip content="Team Settings" relationship="label">
          <Button
            icon={<Settings20Regular />}
            appearance="subtle"
            size="medium"
            aria-label="Team Settings"
            style={{
              display: 'flex',
              gap: '12px',
              alignItems: 'center',
              justifyContent: 'flex-start',
              padding: '0',
              margin: '0',
              height: 'auto',
              minHeight: '40px',
              width: '100%',
              borderRadius: '4px',
              border: 'none',
              background: 'transparent',
            }}
          >
            Settings
          </Button>
        </Tooltip>
      </DialogTrigger>
      <DialogSurface style={{ maxWidth: '600px', width: '90vw', minWidth: '500px' }}>
        <DialogTitle style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Select a Team</span>
          <div>
            <input
              type="file"
              accept=".json"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              id="team-upload-input"
              disabled={uploadLoading}
            />
            <Button
              icon={<CloudAdd20Regular />}
              appearance="outline"
              size="small"
              disabled={uploadLoading}
              onClick={() => document.getElementById('team-upload-input')?.click()}
            >
              {uploadLoading ? <Spinner size="extra-small" /> : 'Upload custom team'}
            </Button>
          </div>
        </DialogTitle>
        <DialogContent style={{ width: '100%', padding: '0' }}>
          <DialogBody style={{ width: '100%', padding: '16px 24px', display: 'block' }}>
            {error && (
              <div style={{ 
                color: '#d13438', 
                marginBottom: '16px',
                padding: '12px',
                backgroundColor: '#fdf2f2',
                border: '1px solid #f5c6cb',
                borderRadius: '4px'
              }}>
                <Text style={{ whiteSpace: 'pre-line' }}>{error}</Text>
              </div>
            )}

            {uploadMessage && (
              <div style={{ 
                color: '#107c10', 
                marginBottom: '16px',
                padding: '12px',
                backgroundColor: '#f3f9f3',
                border: '1px solid #c6e7c6',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <Spinner size="extra-small" />
                <Text>{uploadMessage}</Text>
              </div>
            )}

            {/* Upload requirements info */}
            <div style={{ 
              marginBottom: '16px',
              padding: '12px',
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '4px'
            }}>
              <Text size={300} weight="semibold" style={{ display: 'block', marginBottom: '8px', color: 'inherit' }}>
                Upload Requirements:
              </Text>
              <Text size={200} style={{ display: 'block', lineHeight: '1.4', color: 'inherit' }}>
                • JSON file must contain: <strong>name</strong> and <strong>description</strong><br/>
                • At least one agent with <strong>name</strong>, <strong>type</strong>, <strong>input_key</strong>, and <strong>deployment_name</strong><br/>
                • RAG agents additionally require <strong>index_name</strong> for search functionality<br/>
                • Starting tasks are optional but must have <strong>name</strong> and <strong>prompt</strong> if included<br/>
                • All text fields cannot be empty
              </Text>
            </div>

            {/* Search input */}
            <div style={{ marginBottom: '16px' }}>
              <Input
                placeholder="Search teams..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                contentBefore={<Search20Regular />}
                style={{ width: '100%' }}
              />
            </div>

            {loading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '32px' }}>
                <Spinner label="Loading teams..." />
              </div>
            ) : filteredTeams.length > 0 ? (
              <div style={{ 
                marginBottom: '24px',
                display: 'block',
                width: '100%'
              }}>
                {filteredTeams.map((team) => (
                  <div key={team.team_id} style={{ marginBottom: '8px', width: '100%' }}>
                    {renderTeamCard(team, team.created_by !== 'system')}
                  </div>
                ))}
              </div>
            ) : searchQuery ? (
              <div style={{ 
                marginBottom: '24px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                padding: '32px 16px',
                textAlign: 'center'
              }}>
                <Text size={400} style={{ color: '#666', marginBottom: '8px' }}>
                  No teams found matching "{searchQuery}"
                </Text>
                <Text size={300} style={{ color: '#888' }}>
                  Try a different search term
                </Text>
              </div>
            ) : teams.length === 0 ? (
              <div style={{ 
                marginBottom: '24px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                padding: '32px 16px',
                textAlign: 'center'
              }}>
                <Text size={400} style={{ color: '#666', marginBottom: '8px' }}>
                  No teams available
                </Text>
                <Text size={300} style={{ color: '#888' }}>
                  Upload a JSON team configuration to get started
                </Text>
              </div>
            ) : null}
          </DialogBody>
        </DialogContent>
        <DialogActions>
          <Button appearance="secondary" onClick={handleCancel}>
            Cancel
          </Button>
          <Button 
            appearance="primary" 
            onClick={handleContinue}
            disabled={!tempSelectedTeam}
          >
            Continue
          </Button>
        </DialogActions>
      </DialogSurface>
    </Dialog>

    {/* Delete Confirmation Dialog */}
    <Dialog open={deleteConfirmOpen} onOpenChange={(event, data) => setDeleteConfirmOpen(data.open)}>
      <DialogSurface>
        <DialogContent data-testid="delete-dialog">
          <DialogBody>
            <DialogTitle>⚠️ Delete Team Configuration</DialogTitle>
            <div style={{ marginTop: '16px', marginBottom: '20px' }}>
              <Text style={{ display: 'block', marginBottom: '16px' }}>
                Are you sure you want to delete <strong>"{teamToDelete?.name}"</strong>?
              </Text>
              <div style={{ 
                padding: '16px', 
                backgroundColor: '#fff4e6', 
                border: '1px solid #ffb84d', 
                borderRadius: '6px'
              }}>
                <Text weight="semibold" style={{ 
                  color: '#d83b01', 
                  display: 'block', 
                  marginBottom: '8px'
                }}>
                  Important Notice:
                </Text>
                <Text style={{ lineHeight: '1.4', color: '#323130' }}>
                  This team configuration and its agents are shared across all users in the system. 
                  Deleting this team will permanently remove it for everyone, and this action cannot be undone.
                </Text>
              </div>
            </div>
          </DialogBody>
          <DialogActions>
            <Button 
              appearance="secondary" 
              disabled={deleteLoading}
              onClick={() => {
                setDeleteConfirmOpen(false);
                setTeamToDelete(null);
              }}
            >
              Cancel
            </Button>
            <Button 
              appearance="primary" 
              disabled={deleteLoading}
              style={{ backgroundColor: '#d13438', color: 'white' }}
              onClick={confirmDeleteTeam}
               data-testid="delete-team-confirm"
            >
              {deleteLoading ? 'Deleting...' : 'Delete for Everyone'}
            </Button>
          </DialogActions>
        </DialogContent>
      </DialogSurface>
    </Dialog>
    </>
  );
};

export default SettingsButton;
