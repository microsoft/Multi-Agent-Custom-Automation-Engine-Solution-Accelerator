import { PlanWithSteps, PlanStatus } from '../models';
import { Task } from '../models/taskList';
import { apiService } from '../api/apiService';
import { InputTask, InputTaskResponse } from '../models/inputTask';

/**
 * TaskService - Service for handling task-related operations and transformations
 */
export class TaskService {
    /**
     * Transform PlanWithSteps data into Task arrays for TaskList component
     * @param plansData Array of PlanWithSteps to transform
     * @returns Object containing inProgress and completed task arrays
     */
    static transformPlansToTasks(plansData: PlanWithSteps[]): { inProgress: Task[], completed: Task[] } {
        if (!plansData || plansData.length === 0) {
            return { inProgress: [], completed: [] };
        }

        const inProgress: Task[] = [];
        const completed: Task[] = [];

        plansData.forEach((plan) => {
            const task: Task = {
                id: plan.session_id,
                name: plan.initial_goal,
                status: apiService.isPlanComplete(plan) ? 'completed' : 'inprogress',
                date: new Date(plan.timestamp).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                })
            };

            // Categorize based on plan status and completion
            if (plan.overall_status === PlanStatus.COMPLETED || apiService.isPlanComplete(plan)) {
                completed.push(task);
            } else {
                inProgress.push(task);
            }
        });

        return { inProgress, completed };
    }

    /**
     * Get task statistics from task arrays
     * @param inProgressTasks Array of in-progress tasks
     * @param completedTasks Array of completed tasks
     * @returns Object containing task count statistics
     */
    static getTaskStatistics(inProgressTasks: Task[], completedTasks: Task[]) {
        return {
            inProgressCount: inProgressTasks.length,
            completedCount: completedTasks.length,
            totalCount: inProgressTasks.length + completedTasks.length
        };
    }

    /**
     * Find a task by ID in either task array
     * @param taskId The task ID to search for
     * @param inProgressTasks Array of in-progress tasks
     * @param completedTasks Array of completed tasks
     * @returns The found task or undefined
     */
    static findTaskById(taskId: string, inProgressTasks: Task[], completedTasks: Task[]): Task | undefined {
        return [...inProgressTasks, ...completedTasks].find(task => task.id === taskId);
    }

    /**
     * Filter tasks by status
     * @param tasks Array of tasks to filter
     * @param status Status to filter by
     * @returns Filtered array of tasks
     */
    static filterTasksByStatus(tasks: Task[], status: 'inprogress' | 'completed'): Task[] {
        return tasks.filter(task => task.status === status);
    }

    /**
     * Generate a session ID using the specified algorithm
     * @returns Generated session ID in format "sid_" + timestamp + "_" + random
     */
    static generateSessionId(): string {
        const timestamp = new Date().getTime();
        const random = Math.floor(Math.random() * 10000);
        return `sid_${timestamp}_${random}`;
    }

    /**
     * Submit an input task to create a new plan
     * @param description Task description
     * @returns Promise with the response containing session and plan IDs
     */
    static async submitInputTask(description: string): Promise<InputTaskResponse> {
        const sessionId = this.generateSessionId();

        const inputTask: InputTask = {
            session_id: sessionId,
            description: description
        };

        return await apiService.submitInputTask(inputTask);
    }
}

export default TaskService;
