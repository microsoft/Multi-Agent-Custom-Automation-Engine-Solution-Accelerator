import { Plan, PlanStatus } from "../models";
import { Task } from "../models/taskList";
import { apiService } from "../api/apiService";
import { InputTask, InputTaskResponse } from "../models/inputTask";

/**
 * TaskService - Service for handling task-related operations and transformations
 */
export class TaskService {
  /**
   * Transform PlanWithSteps data into Task arrays for TaskList component
   * @param plansData Array of PlanWithSteps to transform
   * @returns Object containing inProgress and completed task arrays
   */
  static transformPlansToTasks(plansData: Plan[]): {
    inProgress: Task[];
    completed: Task[];
  } {
    if (!plansData || plansData.length === 0) {
      return { inProgress: [], completed: [] };
    }

    const inProgress: Task[] = [];
    const completed: Task[] = [];

    plansData.forEach((plan) => {
      const task: Task = {
        id: plan.session_id,
        name: plan.initial_goal,
        status: plan.overall_status === PlanStatus.COMPLETED ? "completed" : "inprogress",
        date: new Intl.DateTimeFormat(undefined, {
          dateStyle: "long",
          // timeStyle: "short",
        }).format(new Date(plan.timestamp)),
      };

      // Categorize based on plan status and completion
      if (
        plan.overall_status === PlanStatus.COMPLETED
      ) {
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
      totalCount: inProgressTasks.length + completedTasks.length,
    };
  }

  /**
   * Find a task by ID in either task array
   * @param taskId The task ID to search for
   * @param inProgressTasks Array of in-progress tasks
   * @param completedTasks Array of completed tasks
   * @returns The found task or undefined
   */
  static findTaskById(
    taskId: string,
    inProgressTasks: Task[],
    completedTasks: Task[]
  ): Task | undefined {
    return [...inProgressTasks, ...completedTasks].find(
      (task) => task.id === taskId
    );
  }

  /**
   * Filter tasks by status
   * @param tasks Array of tasks to filter
   * @param status Status to filter by
   * @returns Filtered array of tasks
   */
  static filterTasksByStatus(
    tasks: Task[],
    status: "inprogress" | "completed"
  ): Task[] {
    return tasks.filter((task) => task.status === status);
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
   * Split subtask action into description and function/details parts
   * @param action The full action string to split
   * @returns Object containing description and functionOrDetails
   */
  static splitSubtaskAction(action: string): {
    description: string;
    functionOrDetails: string | null;
  } {
    // Check for "Function:" pattern (with period before Function)

    const functionMatch = action.match(/^(.+?)\.\s*Function:\s*(.+)$/);
    if (functionMatch) {
      return {
        description: functionMatch[1].trim(),
        functionOrDetails: functionMatch[2].trim(),
      };
    }

    // Check for any colon pattern - split on first colon
    const colonIndex = action.indexOf(":");
    if (colonIndex !== -1) {
      return {
        description: action.substring(0, colonIndex).trim(),
        functionOrDetails: null,
      };
    }

    // If no colon found, return the full action as description
    return {
      description: action,
      functionOrDetails: null,
    };
  }
  /**
   * Clean text by converting any non-alphanumeric character to spaces
   * @param text The text string to clean
   * @returns Cleaned text string with only letters, numbers, and spaces
   */
  static cleanTextToSpaces(text: string): string {
    if (!text) return "";

    let cleanedText = text
      .replace("Hr_Agent", "HR Agent")
      .replace("Hr Agent", "HR Agent")
      .trim();

    // Convert camelCase and PascalCase to spaces
    // This regex finds lowercase letter followed by uppercase letter
    cleanedText = cleanedText.replace(/([a-z])([A-Z])/g, '$1 $2');

    // Replace any remaining non-alphanumeric characters with spaces
    cleanedText = cleanedText.replace(/[^a-zA-Z0-9]/g, ' ');

    // Clean up multiple spaces and trim
    cleanedText = cleanedText.replace(/\s+/g, ' ').trim();

    // Capitalize each word for better readability
    cleanedText = cleanedText.replace(/\b\w/g, (char) => char.toUpperCase());

    return cleanedText;
  }

  static cleanHRAgent(text: string): string {
    if (!text) return "";
    // Replace any non-alphanumeric character with a space
    let cleanedText = text
      .replace("Hr_Agent", "HR Agent")
      .replace("Hr Agent", "HR Agent")
      .trim();

    return cleanedText;
  }

  /**
   * Create a new plan with RAI validation
   * @param description Task description
   * @param teamId Optional team ID to use for this plan
   * @returns Promise with the response containing plan ID and status
   */
  static async createPlan(
    description: string,
    teamId?: string
  ): Promise<InputTaskResponse> {
    const sessionId = this.generateSessionId();

    const inputTask: InputTask = {
      session_id: sessionId,
      description: description,
      team_id: teamId,
    };

    try {
      return await apiService.createPlan(inputTask);
    } catch (error: any) {

      // You can customize this logic as needed
      let message = "Unable to create plan. Please try again.";

      throw new Error(message);
    }
  }
}

export default TaskService;
