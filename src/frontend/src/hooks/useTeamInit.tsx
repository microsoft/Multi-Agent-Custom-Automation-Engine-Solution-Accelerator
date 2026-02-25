import { useCallback, useEffect, useRef } from "react";
import { TeamConfig } from "../models/Team";
import { ShowToastFn } from "../components/toast/InlineToaster";
import {
    useAppDispatch,
    useAppSelector,
    selectSelectedTeam,
    selectIsLoadingTeam,
    selectRequiresTeamUpload,
    initializeTeam,
    setSelectedTeam,
} from "../store";

export interface UseTeamInitReturn {
    /** The currently selected/initialized team */
    selectedTeam: TeamConfig | null;
    /** Whether team initialization is in progress */
    isLoadingTeam: boolean;
    /** Set the selected team directly */
    setSelectedTeamValue: (team: TeamConfig | null) => void;
    /** Re-initialize the team (e.g. after switching) */
    reinitializeTeam: (force?: boolean) => Promise<void>;
}

/**
 * Hook that encapsulates team initialization from the backend.
 *
 * On mount it dispatches the `initializeTeam` async thunk, which
 * fetches the init response, loads the team list, and selects the
 * matching team — all managed via teamSlice extraReducers.
 *
 * Provides `reinitializeTeam` for team-switch scenarios.
 *
 * @param showToast - toast notification function
 */
export function useTeamInit(
    showToast: ShowToastFn
): UseTeamInitReturn {
    const dispatch = useAppDispatch();
    const selectedTeam = useAppSelector(selectSelectedTeam);
    const isLoadingTeam = useAppSelector(selectIsLoadingTeam);
    const requiresTeamUpload = useAppSelector(selectRequiresTeamUpload);

    // Keep a stable ref so initTeam never re-creates due to showToast identity changes
    const showToastRef = useRef(showToast);
    useEffect(() => {
        showToastRef.current = showToast;
    }, [showToast]);

    const initTeam = useCallback(
        async (force = false) => {
            try {
                const result = await dispatch(initializeTeam(force)).unwrap();

                if (result.requiresUpload) {
                    showToastRef.current(
                        "Welcome! Please upload a team configuration file to get started.",
                        "info"
                    );
                } else if (result.team) {
                    showToastRef.current(
                        `${result.team.name} team initialized successfully with ${result.team.agents?.length || 0} agents`,
                        "success"
                    );
                }
            } catch (_error) {
                console.error("Error initializing team from backend:", _error);
                showToastRef.current(
                    "Team initialization failed. You can still upload a custom team configuration.",
                    "info"
                );
            }
        },
        [dispatch]
    );

    // Auto-init on mount (runs exactly once)
    useEffect(() => {
        initTeam();
    }, [initTeam]);

    const reinitializeTeam = useCallback(
        async (force = true) => {
            await initTeam(force);
        },
        [initTeam]
    );

    const setSelectedTeamValue = useCallback(
        (team: TeamConfig | null) => {
            dispatch(setSelectedTeam(team));
        },
        [dispatch]
    );

    return { selectedTeam, isLoadingTeam, setSelectedTeamValue: setSelectedTeamValue, reinitializeTeam };
}

export default useTeamInit;
