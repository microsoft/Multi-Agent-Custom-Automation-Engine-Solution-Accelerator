import { useCallback, useEffect, useRef, useState } from "react";
import { Plan, Task } from "../models";
import { apiService } from "../api";
import { TaskService } from "../services";

export interface UsePlanListReturn {
    /** All raw plans from the API */
    plans: Plan[] | null;
    /** Completed tasks derived from plans */
    completedTasks: Task[];
    /** Whether plans are currently loading */
    plansLoading: boolean;
    /** Error object if plan loading failed */
    plansError: Error | null;
    /** Manually reload plans (pass `true` to bypass cache) */
    loadPlans: (forceRefresh?: boolean) => Promise<void>;
}

/**
 * Hook that encapsulates plan-list fetching, caching and
 * transformation into tasks.
 *
 * @param reloadTrigger - when `true`, forces a cache-bypassing reload
 * @param onReloadDone  - called after the triggered reload finishes (success or error)
 */
export function usePlanList(
    reloadTrigger = false,
    onReloadDone?: () => void
): UsePlanListReturn {
    const [plans, setPlans] = useState<Plan[] | null>(null);
    const [completedTasks, setCompletedTasks] = useState<Task[]>([]);
    const [plansLoading, setPlansLoading] = useState<boolean>(false);
    const [plansError, setPlansError] = useState<Error | null>(null);

    // Keep onReloadDone in a ref so loadPlans is stable
    const onReloadDoneRef = useRef(onReloadDone);
    useEffect(() => {
        onReloadDoneRef.current = onReloadDone;
    }, [onReloadDone]);

    const loadPlans = useCallback(
        async (forceRefresh = false) => {
            try {
                setPlansLoading(true);
                setPlansError(null);
                const plansData = await apiService.getPlans(undefined, !forceRefresh);
                setPlans(plansData);

                if (forceRefresh && onReloadDoneRef.current) {
                    onReloadDoneRef.current();
                }
            } catch (error) {
                setPlansError(
                    error instanceof Error ? error : new Error("Failed to load plans")
                );
                if (forceRefresh && onReloadDoneRef.current) {
                    onReloadDoneRef.current();
                }
            } finally {
                setPlansLoading(false);
            }
        },
        [] // stable — no external deps
    );

    // Track whether we've already loaded to avoid double-fire on mount
    const hasLoadedRef = useRef(false);

    // Initial load — skip if reloadTrigger is already true (the trigger effect
    // will handle it with a forced refresh, so no need to do a cached load first)
    useEffect(() => {
        if (!reloadTrigger) {
            loadPlans();
            hasLoadedRef.current = true;
        }
        // Only run on mount — loadPlans is stable, reloadTrigger handled below
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Force-refresh when trigger flips to true
    useEffect(() => {
        if (reloadTrigger) {
            loadPlans(true);
            hasLoadedRef.current = true;
        }
    }, [reloadTrigger, loadPlans]);

    // Derive completed tasks from plans
    useEffect(() => {
        if (plans) {
            const { completed } = TaskService.transformPlansToTasks(plans);
            setCompletedTasks(completed);
        }
    }, [plans]);

    return { plans, completedTasks, plansLoading, plansError, loadPlans };
}

export default usePlanList;
