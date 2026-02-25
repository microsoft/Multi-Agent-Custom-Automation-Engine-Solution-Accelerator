import { useCallback, useState } from "react";
import { TeamConfig } from "../models/Team";
import { TeamService } from "../services/TeamService";

export interface FileUploadResult {
    success: boolean;
    team?: TeamConfig;
    error?: string;
    raiError?: boolean;
    modelError?: boolean;
    searchError?: boolean;
}

export interface UseFileUploadReturn {
    /** Whether a file upload is currently in progress */
    uploadLoading: boolean;
    /** User-facing progress/status message */
    uploadMessage: string | null;
    /** Success message after upload */
    uploadSuccessMessage: string | null;
    /** The most recently uploaded team */
    uploadedTeam: TeamConfig | null;
    /** Upload a JSON team-config file (from <input /> onChange) */
    handleFileUpload: (file: File, existingTeams: TeamConfig[]) => Promise<FileUploadResult>;
    /** Reset upload state (e.g. when dialog closes) */
    resetUploadState: () => void;
}

/**
 * Hook that encapsulates team configuration file upload logic,
 * including validation, duplicate checking, and error handling.
 *
 * @param onTeamUpload - optional callback invoked after a successful upload
 */
export function useFileUpload(
    onTeamUpload?: () => Promise<void>
): UseFileUploadReturn {
    const [uploadLoading, setUploadLoading] = useState(false);
    const [uploadMessage, setUploadMessage] = useState<string | null>(null);
    const [uploadSuccessMessage, setUploadSuccessMessage] = useState<string | null>(null);
    const [uploadedTeam, setUploadedTeam] = useState<TeamConfig | null>(null);

    const resetUploadState = useCallback(() => {
        setUploadLoading(false);
        setUploadMessage(null);
        setUploadSuccessMessage(null);
        setUploadedTeam(null);
    }, []);

    const handleFileUpload = useCallback(
        async (file: File, existingTeams: TeamConfig[]): Promise<FileUploadResult> => {
            setUploadLoading(true);
            setUploadMessage("Reading and validating team configuration...");
            setUploadSuccessMessage(null);

            try {
                // Validate file type
                if (!file.name.toLowerCase().endsWith(".json")) {
                    throw new Error("Please upload a valid JSON file");
                }

                // Parse & validate JSON
                const fileText = await file.text();
                let teamData: any;
                try {
                    teamData = JSON.parse(fileText);
                } catch {
                    throw new Error("Invalid JSON file format");
                }

                // Agent count limit
                if (
                    teamData.agents &&
                    Array.isArray(teamData.agents) &&
                    teamData.agents.length > 6
                ) {
                    throw new Error(
                        `Team configuration cannot have more than 6 agents. Your team has ${teamData.agents.length} agents.`
                    );
                }

                // Duplicate check
                if (teamData.name) {
                    const existing = existingTeams.find(
                        (t) =>
                            t.name.toLowerCase() === teamData.name.toLowerCase() ||
                            (teamData.team_id && t.team_id === teamData.team_id)
                    );
                    if (existing) {
                        throw new Error(
                            `A team with the name "${teamData.name}" already exists. Please choose a different name or modify the existing team.`
                        );
                    }
                }

                // Upload
                setUploadMessage("Uploading team configuration...");
                const result = await TeamService.uploadCustomTeam(file);

                if (result.success && result.team) {
                    setUploadMessage(null);
                    setUploadSuccessMessage(`${result.team.name} was uploaded`);
                    setUploadedTeam(result.team);

                    setTimeout(() => setUploadSuccessMessage(null), 15000);

                    if (onTeamUpload) await onTeamUpload();

                    return { success: true, team: result.team };
                }

                // Upload failed — clear the progress message before returning error
                setUploadMessage(null);

                // Backend-specific error categories
                if (result.raiError) {
                    return {
                        success: false,
                        raiError: true,
                        error:
                            "❌ Content Safety Check Failed\n\nYour team configuration contains content that doesn't meet our safety guidelines.",
                    };
                }
                if (result.modelError) {
                    return {
                        success: false,
                        modelError: true,
                        error:
                            "🤖 Model Deployment Validation Failed\n\nYour team configuration references models that are not properly deployed.",
                    };
                }
                if (result.searchError) {
                    return {
                        success: false,
                        searchError: true,
                        error:
                            "🔍 RAG Search Configuration Error\n\nYour team configuration includes RAG/search agents but has search index issues.",
                    };
                }

                return { success: false, error: result.error || "Failed to upload team configuration" };
            } catch (err: any) {
                setUploadMessage(null);
                return { success: false, error: err.message || "Failed to upload team configuration" };
            } finally {
                setUploadLoading(false);
            }
        },
        [onTeamUpload]
    );

    return {
        uploadLoading,
        uploadMessage,
        uploadSuccessMessage,
        uploadedTeam,
        handleFileUpload,
        resetUploadState,
    };
}

export default useFileUpload;
