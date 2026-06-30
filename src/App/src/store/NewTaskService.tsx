
/**
 * Service for handling "New Task" button functionality across different pages
 * Provides reusable methods for navigating to homepage and resetting textarea
 */
export class NewTaskService {
    /**
     * Event name for textarea reset functionality
     */
    private static readonly RESET_TEXTAREA_EVENT = 'resetTextarea';

    /**
     * Handle new task action from PlanPage
     * Navigates to homepage and resets textarea
     * @param navigate - React Router navigate function
     */
    static handleNewTaskFromPlan(navigate: (to: string) => void): void {
        // Navigate to homepage
        navigate('/');

        // Emit event to reset textarea after navigation
        // Use setTimeout to ensure navigation completes first
        setTimeout(() => {
            NewTaskService.resetTextarea();
        }, 100);
    }

    /**
     * Handle new task action from HomePage
     * Resets textarea to empty state
     */
    static handleNewTaskFromHome(): void {
        NewTaskService.resetTextarea();
    }

    /**
     * Reset textarea to empty state
     * Emits a custom event that HomeInput component can listen to
     */
    static resetTextarea(): void {
        const event = new CustomEvent(NewTaskService.RESET_TEXTAREA_EVENT);
        window.dispatchEvent(event);
    }

    /**
     * Add event listener for textarea reset
     * Should be called in HomeInput component
     * @param callback - Function to call when reset event is triggered
     * @returns Cleanup function to remove the event listener
     */
    static addResetListener(callback: () => void): () => void {
        const handleReset = () => {
            callback();
        };

        window.addEventListener(NewTaskService.RESET_TEXTAREA_EVENT, handleReset);

        // Return cleanup function
        return () => {
            window.removeEventListener(NewTaskService.RESET_TEXTAREA_EVENT, handleReset);
        };
    }
}
