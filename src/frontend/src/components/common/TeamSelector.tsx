import React, { useState, useCallback } from 'react';
import {
  Button,
  Dialog,
  DialogTrigger,
  DialogSurface,
  DialogTitle,
  DialogContent,
  DialogBody,
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
  TabList,
  Tooltip
} from '@fluentui/react-components';
import {
  ChevronUpDown16Regular,
  MoreHorizontal20Regular,
  Search20Regular,
  Dismiss20Regular,
  CheckmarkCircle20Filled,
  Delete20Filled
} from '@fluentui/react-icons';
import { TeamConfig } from '../../models/Team';
import { TeamService } from '../../services/TeamService';

import styles from '../../styles/TeamSelector.module.css';

interface TeamSelectorProps {
  onTeamSelect?: (team: TeamConfig | null) => void;
  onTeamUpload?: () => Promise<void>;
  selectedTeam?: TeamConfig | null;
  isHomePage: boolean;
}

const TeamSelector: React.FC<TeamSelectorProps> = ({
  onTeamSelect,
  onTeamUpload,
  selectedTeam,
  isHomePage,
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
  const [selectionLoading, setSelectionLoading] = useState(false);
  const [uploadedTeam, setUploadedTeam] = useState<TeamConfig | null>(null);
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState<string | null>(null);
  // Helper function to check if a team is a default team
  const isDefaultTeam = (team: TeamConfig): boolean => {
    const defaultTeamIds = ['team-1', 'team-2', 'team-3'];
    const defaultTeamNames = ['Human Resources Team', 'Product Marketing Team', 'Retail Customer Success Team'];
    
    return defaultTeamIds.includes(team.team_id) || 
           defaultTeamNames.includes(team.name);
  };
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
      setUploadedTeam(null);
      setUploadSuccessMessage(null);
    } else {
      setTempSelectedTeam(null);
      setError(null);
      setUploadMessage(null);
      setSearchQuery('');
      setUploadedTeam(null);
      setUploadSuccessMessage(null);
    }
  };

  const handleContinue = async () => {
    if (!tempSelectedTeam) return;

    setSelectionLoading(true);
    setError(null);

    try {
      // If this team was just uploaded, skip the selection API call and go directly to homepage
      if (uploadedTeam && uploadedTeam.team_id === tempSelectedTeam.team_id) {
        console.log('Uploaded team selected, going directly to homepage:', tempSelectedTeam.name);
        onTeamSelect?.(tempSelectedTeam);
        setIsOpen(false);
        return; // Skip the selectTeam API call
      }

      // For existing teams, do the normal selection process
      const result = await TeamService.selectTeam(tempSelectedTeam.team_id);

      if (result.success) {
        console.log('Team selected:', result.data);
        onTeamSelect?.(tempSelectedTeam);
        setIsOpen(false);
      } else {
        setError(result.error || 'Failed to select team');
      }
    } catch (err: any) {
      console.error('Error selecting team:', err);
      setError('Failed to select team. Please try again.');
    } finally {
      setSelectionLoading(false);
    }
  };

  const handleCancel = () => {
    setTempSelectedTeam(null);
    setIsOpen(false);
  };

  const filteredTeams = teams
    .filter(team => {
      const searchLower = searchQuery.toLowerCase();
      const nameMatch = team.name && team.name.toLowerCase().includes(searchLower);
      const descriptionMatch = team.description && team.description.toLowerCase().includes(searchLower);
      return nameMatch || descriptionMatch;
    })
    .sort((a, b) => {
      const aIsUploaded = uploadedTeam?.team_id === a.team_id;
      const bIsUploaded = uploadedTeam?.team_id === b.team_id;

      if (aIsUploaded && !bIsUploaded) return -1;
      if (!aIsUploaded && bIsUploaded) return 1;

      return 0;
    });

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
      const success = await TeamService.deleteTeam(teamToDelete.team_id);

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
    setUploadSuccessMessage(null);

    try {
      if (!file.name.toLowerCase().endsWith('.json')) {
        throw new Error('Please upload a valid JSON file');
      }

      const fileText = await file.text();
      let teamData;
      try {
        teamData = JSON.parse(fileText);
      } catch (parseError) {
        throw new Error('Invalid JSON file format');
      }

      if (teamData.agents && Array.isArray(teamData.agents) && teamData.agents.length > 6) {
        throw new Error(`Team configuration cannot have more than 6 agents. Your team has ${teamData.agents.length} agents.`);
      }

      // Check for duplicate team names or IDs
      if (teamData.name) {
        const existingTeam = teams.find(team =>
          team.name.toLowerCase() === teamData.name.toLowerCase() ||
          (teamData.team_id && team.team_id === teamData.team_id)
        );

        if (existingTeam) {
          throw new Error(`A team with the name "${teamData.name}" already exists. Please choose a different name or modify the existing team.`);
        }
      }

      setUploadMessage('Uploading team configuration...');
      const result = await TeamService.uploadCustomTeam(file);

      if (result.success) {
        setUploadMessage(null);

        if (result.team) {
          // Set success message with team name
          setUploadSuccessMessage(`${result.team.name} was uploaded`);

          setTeams(currentTeams => [result.team!, ...currentTeams]);
          setUploadedTeam(result.team);
          setTempSelectedTeam(result.team);

          setTimeout(() => {
            setUploadSuccessMessage(null);
          }, 15000);
        }

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
    setUploadSuccessMessage(null);

    try {
      const fileText = await file.text();
      let teamData;
      try {
        teamData = JSON.parse(fileText);
      } catch (parseError) {
        throw new Error('Invalid JSON file format');
      }

      if (teamData.agents && Array.isArray(teamData.agents) && teamData.agents.length > 6) {
        throw new Error(`Team configuration cannot have more than 6 agents. Your team has ${teamData.agents.length} agents.`);
      }

      // Check for duplicate team names or IDs
      if (teamData.name) {
        const existingTeam = teams.find(team =>
          team.name.toLowerCase() === teamData.name.toLowerCase() ||
          (teamData.team_id && team.team_id === teamData.team_id)
        );

        if (existingTeam) {
          throw new Error(`A team with the name "${teamData.name}" already exists. Please choose a different name or modify the existing team.`);
        }
      }

      setUploadMessage('Uploading team configuration...');
      const result = await TeamService.uploadCustomTeam(file);

      if (result.success) {
        setUploadMessage(null);

        if (result.team) {
          // Set success message with team name
          setUploadSuccessMessage(`${result.team.name} was uploaded and selected`);

          setTeams(currentTeams => [result.team!, ...currentTeams]);
          setUploadedTeam(result.team);
          setTempSelectedTeam(result.team);

          // Clear success message after 15 seconds if user doesn't act
          setTimeout(() => {
            setUploadSuccessMessage(null);
          }, 15000);
        }

        if (onTeamUpload) {
          await onTeamUpload();
        }
      } else if (result.raiError) {
        setError(' Content Safety Check Failed\n\nYour team configuration contains content that doesn\'t meet our safety guidelines.');
        setUploadMessage(null);
      } else if (result.modelError) {
        setError(' Model Deployment Validation Failed\n\nYour team configuration references models that are not properly deployed.');
        setUploadMessage(null);
      } else if (result.searchError) {
        setError(' RAG Search Configuration Error\n\nYour team configuration includes RAG/search agents but has search index issues.');
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

  const renderTeamCard = (team: TeamConfig, index?: number) => {
    const isSelected = tempSelectedTeam?.team_id === team.team_id;
    const isDefault = isDefaultTeam(team);
    return (
      <div
        key={team.team_id || `team-${index}`}
        className={`${styles.teamCard} ${isSelected ? styles.teamCardSelected : ''}`}
        onClick={() => setTempSelectedTeam(team)}
      >
        {/* Radio Button */}
        <Radio
          checked={isSelected}
          value={team.team_id || `team-${index}`}
          className={styles.teamRadio}
        />

        {/* Team Content */}
        <div className={styles.teamContent}>
          {/* Team name */}
          <div className={styles.teamName}>
            {team.name}
          </div>

          {/* Team description */}
          <div className={styles.teamDescription}>
            {team.description}
          </div>

        </div>

        {/* Agent badges - show agent names only */}
        <div className={styles.agentTags}>
          {team.agents.slice(0, 4).map((agent) => (
            <Badge
              key={`${team.team_id}-agent-${agent.input_key || agent.name}`}
              className={styles.agentBadge}
              appearance="tint"
              size="small"
            >
              {agent.name}
            </Badge>
          ))}
          {team.agents.length > 4 && (
            <Badge
              key={`${team.team_id}-overflow`}
              className={styles.agentBadge}
              appearance="tint"
              size="small"
            >
              +{team.agents.length - 4}
            </Badge>
          )}
        </div>

        {/* Three-dot Menu Button */}
        {isDefault ? (
          <Tooltip
            content="Default teams cannot be deleted."
            relationship="label"
            positioning="above-start"
            withArrow
            mountNode={document.querySelector('[role="dialog"]') || undefined}
          >
            <Button
              icon={<MoreHorizontal20Regular />}
              appearance="subtle"
              size="small"
              disabled={true}
              className={`${styles.moreButton} ${styles.moreButtonDisabled || ''}`}
              onClick={(e) => e.stopPropagation()}
            />
          </Tooltip>
        ) : (
          <Button
            icon={<MoreHorizontal20Regular />}
            appearance="subtle"
            size="small"
            onClick={(e) => handleDeleteTeam(team, e)}
            className={styles.moreButton}
          />
        )}
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
            <span>Select a Team</span>
            <Button
              icon={<Dismiss20Regular />}
              appearance="subtle"
              size="small"
              onClick={handleCancel}
              className={styles.closeButton}
            />
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
                    Upload teams
                  </Tab>
                </TabList>
              </div>

              <div className={styles.tabContentContainer}>
                {activeTab === 'teams' && (
                  <div className={styles.teamsTabContent}>
                    {error && (
                      <div className={styles.errorMessage}>
                        <Text className={styles.errorText}>{error}</Text>
                      </div>
                    )}

                    <div className={styles.searchContainer}>
                      <div style={{ position: 'relative', width: '100%' }}>
                        <Input
                          className={styles.searchInput}
                          placeholder="Search teams..."
                          value={searchQuery}
                          onChange={(e, data) => {
                            console.log('Search changed:', data.value);
                            setSearchQuery(data.value || '');
                          }}
                          contentBefore={<Search20Regular />}
                          autoComplete="off"
                          style={{
                            width: '100%',
                            pointerEvents: 'auto',
                            zIndex: 1,
                            position: 'relative'
                          }}
                        />
                      </div>
                    </div>

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
                            {filteredTeams.map((team, index) => renderTeamCard(team, index))}
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

                    {/* Always show the drop zone with dashed border */}
                    <div
                      className={styles.dropZone}
                      onDragOver={uploadSuccessMessage ? undefined : handleDragOver}
                      onDragLeave={uploadSuccessMessage ? undefined : handleDragLeave}
                      onDrop={uploadSuccessMessage ? undefined : handleDrop}
                      onClick={uploadSuccessMessage ? undefined : () => document.getElementById('team-upload-input')?.click()}
                    >
                      {uploadSuccessMessage ? (
                        // Show success message inside the dashed border
                        <div className={styles.dropZoneSuccessContent}>
                          <CheckmarkCircle20Filled className={styles.successIcon} />
                          <Text className={styles.successText}>{uploadSuccessMessage}</Text>
                        </div>
                      ) : (
                        // Show normal upload content
                        <>
                          <div className={styles.dropZoneContent}>
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
                        </>
                      )}
                    </div>

                    <div className={styles.requirementsBox}>
                      <Text className={styles.requirementsTitle}>
                        Upload Requirements
                      </Text>
                      <ul className={styles.requirementsList}>
                        <li key="req-basic" className={styles.requirementsItem}>
                          <Text className={styles.requirementsText}>
                            JSON must include <strong className={styles.requirementsStrong}>name</strong>, <strong className={styles.requirementsStrong}>description</strong>, and <strong className={styles.requirementsStrong}>status</strong>
                          </Text>
                        </li>
                        <li key="req-agents" className={styles.requirementsItem}>
                          <Text className={styles.requirementsText}>
                            At least one agent with <strong className={styles.requirementsStrong}>name</strong>, <strong className={styles.requirementsStrong}>type</strong>, <strong className={styles.requirementsStrong}>input_key</strong>, and <strong className={styles.requirementsStrong}>deployment_name</strong>
                          </Text>
                        </li>
                        <li key="req-max-agents" className={styles.requirementsItem}>
                          <Text className={styles.requirementsText}>
                            Maximum of <strong className={styles.requirementsStrong}>6 agents</strong> per team configuration
                          </Text>
                        </li>
                        <li key="req-rag-agents" className={styles.requirementsItem}>
                          <Text className={styles.requirementsText}>
                            RAG agents additionally require <strong className={styles.requirementsStrong}>index_name</strong>
                          </Text>
                        </li>
                        <li key="req-starting-tasks" className={styles.requirementsItem}>
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


          {tempSelectedTeam && (
            <div className={styles.dialogActions}>
              <Button
                appearance="primary"
                onClick={handleContinue}
                disabled={!tempSelectedTeam || selectionLoading}
                className={styles.continueButton}
              >
                {selectionLoading ? 'Selecting...' : 'Continue'}
              </Button>
            </div>
          )}
        </DialogSurface>
      </Dialog>

      <Dialog open={deleteConfirmOpen} onOpenChange={(event, data) => setDeleteConfirmOpen(data.open)}>
        <DialogSurface className={styles.deleteDialogSurface}>
          <DialogContent className={styles.deleteDialogContent}>
            <DialogBody className={styles.deleteDialogBody}>
              <DialogTitle className={styles.deleteDialogTitle}>
                Are you sure you want to delete "{teamToDelete?.name}"?
              </DialogTitle>
              <Text className={styles.deleteConfirmText}>
                This team configurations and its agents are shared across all users in the system. Deleting this team will permanently remove it for everyone, and this action cannot be undone.
              </Text>
            </DialogBody>
            <div className={styles.deleteDialogActions}>
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
                icon={<Delete20Filled className={styles.deleteIcon} />}
                style={{ backgroundColor: 'var(--colorStatusDangerBackground1)' }}
              >
                {deleteLoading ? 'Deleting...' : 'Delete for Everyone'}
              </Button>
            </div>
          </DialogContent>
        </DialogSurface>
      </Dialog>
    </>
  );
};

export default TeamSelector;