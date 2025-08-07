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
} from '@fluentui/react-components';
import {
  Settings20Regular,
  CloudAdd20Regular,
  Delete20Regular,
  Checkmark20Filled,
} from '@fluentui/react-icons';
import { TeamConfig } from '../../models/Team';
import { TeamService } from '../../services/TeamService';

interface SettingsButtonProps {
  onTeamSelect?: (team: TeamConfig) => void;
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
  const [tempSelectedTeam, setTempSelectedTeam] = useState<TeamConfig | null>(null);

  const loadTeams = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('SettingsButton: Loading teams...');
      // Get all teams from the API (no separation between default and user teams)
      const teamsData = await TeamService.getUserTeams();
      console.log('SettingsButton: Teams loaded:', teamsData);
      console.log('SettingsButton: Number of teams:', teamsData.length);
      setTeams(teamsData);
    } catch (err: any) {
      console.error('SettingsButton: Error loading teams:', err);
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
    } else {
      setTempSelectedTeam(null);
    }
  };

  const handleTeamCardClick = (team: TeamConfig) => {
    setTempSelectedTeam(team);
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

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    console.log('SettingsButton: Starting file upload for:', file.name);
    setUploadLoading(true);
    setError(null);

    try {
      const result = await TeamService.uploadCustomTeam(file);
      console.log('SettingsButton: Upload result:', result);
      if (result.success) {
        console.log('SettingsButton: Upload successful, reloading teams...');
        // Reload teams to include the new custom team
        await loadTeams();
        console.log('SettingsButton: Teams reloaded after upload');
        // Notify parent component about the upload
        if (onTeamUpload) {
          console.log('SettingsButton: Notifying parent about upload...');
          await onTeamUpload();
        }
      } else {
        console.error('SettingsButton: Upload failed:', result.error);
        setError(result.error || 'Failed to upload team configuration');
      }
    } catch (err: any) {
      console.error('SettingsButton: Upload exception:', err);
      setError(err.message || 'Failed to upload team configuration');
    } finally {
      setUploadLoading(false);
      // Reset the input
      event.target.value = '';
    }
  };

  const handleDeleteTeam = async (teamId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    try {
      const success = await TeamService.deleteTeam(teamId);
      if (success) {
        await loadTeams();
      } else {
        setError('Failed to delete team');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete team');
    }
  };

  const renderTeamCard = (team: TeamConfig, isCustom = false) => {
    const isSelected = tempSelectedTeam?.team_id === team.team_id;
    
    return (
      <Card
        style={{
          cursor: 'pointer',
          border: isSelected ? '2px solid #6264a7' : '1px solid #e1e1e1',
          borderRadius: '8px',
          position: 'relative',
          transition: 'all 0.2s ease',
          backgroundColor: isSelected ? '#f0f0ff' : 'white',
          padding: '12px',
          width: '100%',
          boxSizing: 'border-box',
          display: 'block',
        }}
        onClick={() => handleTeamCardClick(team)}
      >
        {/* Team Icon and Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <div style={{
            backgroundColor: '#f8f9fa',
            borderRadius: '4px',
            padding: '4px',
            width: '35px',
            height: '35px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <span style={{ fontSize: '20px' }}>{team.logo}</span>
          </div>
          
          <div style={{ flex: 1, minWidth: 0 }}>
            <Body1 style={{ 
              fontWeight: '600', 
              fontSize: '16px',
              margin: 0,
              color: '#333'
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

          {/* Delete Button for Custom Teams */}
          {isCustom && !isSelected && (
            <Tooltip content="Delete custom team" relationship="label">
              <Button
                icon={<Delete20Regular />}
                appearance="subtle"
                size="small"
                onClick={(e) => handleDeleteTeam(team.team_id, e)}
                style={{ backgroundColor: 'rgba(255, 255, 255, 0.9)' }}
              />
            </Tooltip>
          )}
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
            marginBottom: '16px', 
            fontSize: '14px',
            color: '#333',
            display: 'block'
          }}>
            Agents
          </Body2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
            {team.agents.map((agent) => (
              <Badge
                key={agent.id}
                appearance="outline"
                style={{
                  backgroundColor: '#f8f9fa',
                  border: '1px solid #e1e1e1',
                  color: '#333',
                  fontSize: '12px',
                  padding: '4px 8px',
                  borderRadius: '4px',
                }}
              >
                {agent.name.replace(' Agent', '')}
              </Badge>
            ))}
          </div>
        </div>
      </Card>
    );
  };

  return (
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
              <div style={{ color: 'red', marginBottom: '16px' }}>
                <Text>{error}</Text>
              </div>
            )}

            {loading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '32px' }}>
                <Spinner label="Loading teams..." />
              </div>
            ) : (
              <div style={{ 
                marginBottom: '24px',
                display: 'block',
                width: '100%'
              }}>
                {teams.map((team) => (
                  <div key={team.team_id} style={{ marginBottom: '8px', width: '100%' }}>
                    {renderTeamCard(team, team.created_by !== 'system')}
                  </div>
                ))}
              </div>
            )}
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
  );
};

export default SettingsButton;
