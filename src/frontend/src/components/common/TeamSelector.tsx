import React, { useState, useCallback } from 'react';
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
  Badge,
  Input,
  Radio,
  RadioGroup,
  Tab,
  TabList
} from '@fluentui/react-components';
import {
  ChevronDown16Regular,
  ChevronUpDown16Regular,
  CloudAdd20Regular,
  Delete20Regular,
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
import styles from './TeamSelector.module.css';

// Icon mapping function to convert string icons to FluentUI icons
const getIconFromString = (iconString: string): React.ReactNode => {
  const iconMap: Record<string, React.ReactNode> = {
    'Terminal': <WindowConsole20Regular />,
    'MonitorCog': <Desktop20Regular />,
    'BookMarked': <BookmarkMultiple20Regular />,
    'Search': <Search20Regular />,
    'Robot': <Person20Regular />,
    'Code': <Code20Regular />,
    'Play': <Play20Regular />,
    'Shield': <Shield20Regular />,
    'Globe': <Globe20Regular />,
    'Person': <Person20Regular />,
    'Database': <Database20Regular />,
    'Document': <Document20Regular />,
    'Wrench': <Wrench20Regular />,
    'TestTube': <Clipboard20Regular />,
    'Building': <Building20Regular />,
    'Desktop': <Desktop20Regular />,
    'default': <Person20Regular />,
  };
  
  return iconMap[iconString] || iconMap['default'] || <Person20Regular />;
};

interface TeamSelectorProps {
  onTeamSelect?: (team: TeamConfig | null) => void;
  onTeamUpload?: () => Promise<void>;
  selectedTeam?: TeamConfig | null;
}

const TeamSelector: React.FC<TeamSelectorProps> = ({
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
  const [activeTab, setActiveTab] = useState<string>('teams');

  const loadTeams = async () => {
    setLoading(true);
    setError(null);
    try {
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
      setSearchQuery('');
      setActiveTab('teams');
    } else {
      setTempSelectedTeam(null);
      setError(null);
      setUploadMessage(null);
      setSearchQuery('');
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

  const handleDeleteTeam = (team: TeamConfig, event: React.MouseEvent) => {
    event.stopPropagation();
    setTeamToDelete(team);
    setDeleteConfirmOpen(true);
  };

  const confirmDeleteTeam = async () => {
    if (!teamToDelete || deleteLoading) return;
    
    if (teamToDelete.protected) {
      setError('This team is protected and cannot be deleted.');
      setDeleteConfirmOpen(false);
      setTeamToDelete(null);
      return;
    }
    
    setDeleteLoading(true);
    
    try {
      const success = await TeamService.deleteTeam(teamToDelete.id);
      
      if (success) {
        setDeleteConfirmOpen(false);
        setTeamToDelete(null);
        setDeleteLoading(false);
        
        if (tempSelectedTeam?.team_id === teamToDelete.team_id) {
          setTempSelectedTeam(null);
          if (selectedTeam?.team_id === teamToDelete.team_id) {
            onTeamSelect?.(null);
          }
        }
        
        setTeams(currentTeams => currentTeams.filter(team => team.id !== teamToDelete.id));
        await loadTeams();
      } else {
        setError('Failed to delete team configuration.');
        setDeleteConfirmOpen(false);
        setTeamToDelete(null);
      }
    } catch (err: any) {
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

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadLoading(true);
    setError(null);
    setUploadMessage('Reading and validating team configuration...');

    try {
      if (!file.name.toLowerCase().endsWith('.json')) {
        throw new Error('Please upload a valid JSON file');
      }

      // Read and parse the JSON file to check agent count
      const fileText = await file.text();
      let teamData;
      try {
        teamData = JSON.parse(fileText);
      } catch (parseError) {
        throw new Error('Invalid JSON file format');
      }

      // Check if the team has more than 6 agents
      if (teamData.agents && Array.isArray(teamData.agents) && teamData.agents.length > 6) {
        throw new Error(`Team configuration cannot have more than 6 agents. Your team has ${teamData.agents.length} agents.`);
      }

      setUploadMessage('Uploading team configuration...');
      const result = await TeamService.uploadCustomTeam(file);
      
      if (result.success) {
        setUploadMessage('Team uploaded successfully!');
        
        // Immediately add the team to local state for instant visibility
        if (result.team) {
          setTeams(currentTeams => [...currentTeams, result.team!]);
        }
        
        // Also reload teams from server in the background to ensure consistency
        setTimeout(() => {
          loadTeams().catch(console.error);
        }, 1000);
        
        setUploadMessage(null);
        if (onTeamUpload) {
          await onTeamUpload();
        }
      } else if (result.raiError) {
        setError('❌ Content Safety Check Failed\n\nYour team configuration contains content that doesn\'t meet our safety guidelines.');
        setUploadMessage(null);
      } else if (result.modelError) {
        setError('🤖 Model Deployment Validation Failed\n\nYour team configuration references models that are not properly deployed.');
        setUploadMessage(null);
      } else if (result.searchError) {
        setError('🔍 RAG Search Configuration Error\n\nYour team configuration includes RAG/search agents but has search index issues.');
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
      event.target.value = '';
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.add(styles.dropZoneHover);
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove(styles.dropZoneHover);
  };

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    
    // Reset visual state
    event.currentTarget.classList.remove(styles.dropZoneHover);

    const files = event.dataTransfer.files;
    if (files.length === 0) return;

    const file = files[0];
    if (!file.name.toLowerCase().endsWith('.json')) {
      setError('Please upload a valid JSON file');
      return;
    }

    setUploadLoading(true);
    setError(null);
    setUploadMessage('Reading and validating team configuration...');

    try {
      // Read and parse the JSON file to check agent count
      const fileText = await file.text();
      let teamData;
      try {
        teamData = JSON.parse(fileText);
      } catch (parseError) {
        throw new Error('Invalid JSON file format');
      }

      // Check if the team has more than 6 agents
      if (teamData.agents && Array.isArray(teamData.agents) && teamData.agents.length > 6) {
        throw new Error(`Team configuration cannot have more than 6 agents. Your team has ${teamData.agents.length} agents.`);
      }

      setUploadMessage('Uploading team configuration...');
      const result = await TeamService.uploadCustomTeam(file);
      
      if (result.success) {
        setUploadMessage('Team uploaded successfully!');
        
        // Immediately add the team to local state for instant visibility
        if (result.team) {
          setTeams(currentTeams => [...currentTeams, result.team!]);
        }
        
        // Also reload teams from server in the background to ensure consistency
        setTimeout(() => {
          loadTeams().catch(console.error);
        }, 1000);
        
        setUploadMessage(null);
        if (onTeamUpload) {
          await onTeamUpload();
        }
      } else if (result.raiError) {
        setError('❌ Content Safety Check Failed\n\nYour team configuration contains content that doesn\'t meet our safety guidelines.');
        setUploadMessage(null);
      } else if (result.modelError) {
        setError('🤖 Model Deployment Validation Failed\n\nYour team configuration references models that are not properly deployed.');
        setUploadMessage(null);
      } else if (result.searchError) {
        setError('🔍 RAG Search Configuration Error\n\nYour team configuration includes RAG/search agents but has search index issues.');
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
    }
  };

  const renderTeamCard = (team: TeamConfig) => {
    const isSelected = tempSelectedTeam?.team_id === team.team_id;
    
    return (
      <div 
        key={team.team_id} 
        className={`${styles.teamItem} ${isSelected ? styles.teamItemSelected : ''}`}
        onClick={() => setTempSelectedTeam(team)}
      >
        {/* Radio Button */}
        <Radio
          checked={isSelected}
          value={team.team_id}
        />

        {/* Team Info */}
        <div className={styles.teamInfo}>
          <div className={styles.teamName}>
            {team.name}
          </div>
          <div className={styles.teamDescription}>
            {team.description}
          </div>
        </div>

        {/* Tags */}
        <div className={styles.teamBadges}>
          {team.agents.slice(0, 3).map((agent) => (
            <Badge
              key={agent.input_key}
              className={styles.agentBadge}
              appearance="tint"
              size="small"
            >
              {agent.icon && (
                <span className={styles.badgeIcon}>
                  {getIconFromString(agent.icon)}
                </span>
              )}
              {agent.type}
            </Badge>
          ))}
          {team.agents.length > 3 && (
            <Badge
              className={styles.agentBadge}
              appearance="tint"
              size="small"
            >
              +{team.agents.length - 3}
            </Badge>
          )}
        </div>

        {/* Delete Button */}
        <Button
          icon={<Delete20Regular />}
          appearance="subtle"
          size="small"
          onClick={(e) => handleDeleteTeam(team, e)}
          className={styles.deleteButton}
        />
      </div>
    );
  };

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(event, data) => handleOpenChange(data.open)}>
        <DialogTrigger disableButtonEnhancement>
          <Button
            appearance="subtle"
            className={styles.teamSelectorButton}
            size="medium"
          >
            <div className={styles.teamSelectorContent}>
              <Caption1 className={styles.currentTeamLabel}>
                Current Team
              </Caption1>
              <Body1 className={styles.currentTeamName}>
                {selectedTeam ? selectedTeam.name : 'No team selected'}
              </Body1>
            </div>
            <ChevronUpDown16Regular className={styles.chevronIcon} />
          </Button>
        </DialogTrigger>
        <DialogSurface className={styles.dialogSurface}>
          <DialogTitle className={styles.dialogTitle}>
            Select a Team
          </DialogTitle>
          <DialogContent className={styles.dialogContent}>
            <DialogBody className={styles.dialogBody}>
              <div className={styles.tabContainer}>
                <TabList
                  className={styles.tabList}
                  selectedValue={activeTab}
                  onTabSelect={(event, data) => setActiveTab(data.value as string)}
                >
                  <Tab 
                    value="teams"
                    className={`${styles.tab} ${activeTab === 'teams' ? styles.tabSelected : ''}`}
                  >
                    Teams
                  </Tab>
                  <Tab 
                    value="upload"
                    className={`${styles.tab} ${activeTab === 'upload' ? styles.tabSelected : ''}`}
                  >
                    Upload Team
                  </Tab>
                </TabList>
              </div>

              {/* Tab Content - Directly below tabs without separation */}
              <div className={styles.tabContentContainer}>
                {activeTab === 'teams' && (
                <div className={styles.teamsTabContent}>
                  {error && (
                    <div className={styles.errorMessage}>
                      <Text className={styles.errorText}>{error}</Text>
                    </div>
                  )}

                  {/* Search Input */}
                  <div className={styles.searchContainer}>
                    <Input
                      className={styles.searchInput}
                      placeholder="Search teams..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      contentBefore={<Search20Regular />}
                    />
                  </div>

                  {/* Teams List */}
                  {loading ? (
                    <div className={styles.loadingContainer}>
                      <Spinner label="Loading teams..." />
                    </div>
                  ) : filteredTeams.length > 0 ? (
                    <div className={styles.teamsContainer}>
                      <RadioGroup 
                        value={tempSelectedTeam?.team_id || ''}
                        className={styles.radioGroup}
                      >
                        <div className={styles.teamsList}>
                          {filteredTeams.map((team) => renderTeamCard(team))}
                        </div>
                      </RadioGroup>
                    </div>
                  ) : searchQuery ? (
                    <div className={styles.noTeamsContainer}>
                      <Text size={400} className={styles.noTeamsText}>
                        No teams found matching "{searchQuery}"
                      </Text>
                    </div>
                  ) : (
                    <div className={styles.noTeamsContainer}>
                      <Text size={400} className={styles.noTeamsText}>
                        No teams available
                      </Text>
                      <Text size={300} className={styles.noTeamsSubtext}>
                        Upload a JSON team configuration to get started
                      </Text>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'upload' && (
                <div className={styles.uploadTabContent}>
                  {uploadMessage && (
                    <div className={styles.uploadMessage}>
                      <Spinner size="extra-small" />
                      <Text>{uploadMessage}</Text>
                    </div>
                  )}

                  {error && (
                    <div className={styles.errorMessage}>
                      <Text className={styles.errorText}>{error}</Text>
                    </div>
                  )}

                  {/* Drag and Drop Zone */}
                  <div 
                    className={styles.dropZone}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => document.getElementById('team-upload-input')?.click()}
                  >
                    <div className={styles.dropZoneContent}>
                      {/* <div className={styles.uploadIcon}>
                        ↑
                      </div> */}
                      <Text className={styles.uploadTitle}>
                        Drag & drop your team JSON here
                      </Text>
                      <Text className={styles.uploadSubtitle}>
                        or <span className={styles.browseLink}>click to browse</span>
                      </Text>
                    </div>
                    
                    <input
                      type="file"
                      accept=".json"
                      onChange={handleFileUpload}
                      className={styles.hiddenInput}
                      id="team-upload-input"
                      disabled={uploadLoading}
                    />
                  </div>

                  {/* Upload Requirements */}
                  <div className={styles.requirementsBox}>
                    <Text className={styles.requirementsTitle}>
                      Upload Requirements
                    </Text>
                    <ul className={styles.requirementsList}>
                      <li className={styles.requirementsItem}>
                        <Text className={styles.requirementsText}>
                          JSON must include <strong className={styles.requirementsStrong}>name</strong>, <strong className={styles.requirementsStrong}>description</strong>, and <strong className={styles.requirementsStrong}>status</strong>
                        </Text>
                      </li>
                      <li className={styles.requirementsItem}>
                        <Text className={styles.requirementsText}>
                          At least one agent with <strong className={styles.requirementsStrong}>name</strong>, <strong className={styles.requirementsStrong}>type</strong>, <strong className={styles.requirementsStrong}>input_key</strong>, and <strong className={styles.requirementsStrong}>deployment_name</strong>
                        </Text>
                      </li>
                      <li className={styles.requirementsItem}>
                        <Text className={styles.requirementsText}>
                          Maximum of <strong className={styles.requirementsStrong}>6 agents</strong> per team configuration
                        </Text>
                      </li>
                      <li className={styles.requirementsItem}>
                        <Text className={styles.requirementsText}>
                          RAG agents additionally require <strong className={styles.requirementsStrong}>index_name</strong>
                        </Text>
                      </li>
                      <li className={styles.requirementsItem}>
                        <Text className={styles.requirementsText}>
                          Starting tasks are optional, but if provided must include <strong className={styles.requirementsStrong}>name</strong> and <strong className={styles.requirementsStrong}>prompt</strong>
                        </Text>
                      </li>
                    </ul>
                  </div>
                </div>
              )}
              </div>
            </DialogBody>
          </DialogContent>
          <DialogActions className={styles.dialogActions}>
            <Button 
              appearance="secondary" 
              onClick={handleCancel}
              className={styles.cancelButton}
            >
              Cancel
            </Button>
            <Button 
              appearance="primary" 
              onClick={handleContinue}
              disabled={!tempSelectedTeam}
              className={styles.continueButton}
            >
              Continue
            </Button>
          </DialogActions>
        </DialogSurface>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={(event, data) => setDeleteConfirmOpen(data.open)}>
        <DialogSurface className={styles.deleteDialogSurface}>
          <DialogContent className={styles.deleteDialogContent}>
            <DialogBody className={styles.deleteDialogBody}>
              <DialogTitle className={styles.deleteDialogTitle}>⚠️ Delete Team Configuration</DialogTitle>
              <div>
                <Text className={styles.deleteConfirmText}>
                  Are you sure you want to delete <strong>"{teamToDelete?.name}"</strong>?
                </Text>
                <div className={styles.warningBox}>
                  <Text className={styles.warningText}>
                    This action cannot be undone and will remove the team for all users.
                  </Text>
                </div>
              </div>
            </DialogBody>
            <DialogActions className={styles.deleteDialogActions}>
              <Button 
                appearance="secondary" 
                disabled={deleteLoading}
                onClick={() => {
                  setDeleteConfirmOpen(false);
                  setTeamToDelete(null);
                }}
                className={styles.cancelButton}
              >
                Cancel
              </Button>
              <Button 
                appearance="primary" 
                disabled={deleteLoading}
                className={styles.deleteConfirmButton}
                onClick={confirmDeleteTeam}
              >
                {deleteLoading ? 'Deleting...' : 'Delete Team'}
              </Button>
            </DialogActions>
          </DialogContent>
        </DialogSurface>
      </Dialog>
    </>
  );
};

export default TeamSelector;
