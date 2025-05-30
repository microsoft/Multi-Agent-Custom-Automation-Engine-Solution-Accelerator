import { apiClient } from './apiClient';
import { InputTask, InputTaskResponse } from '../models';

/**
 * Service for submitting and working with user input tasks
 */
export const taskService = {
    /**
     * Submit a new input task to generate a plan
     * @param inputTask The task description and optional session ID
     * @returns Promise with the response containing session and plan IDs
     */
    async submitInputTask(inputTask: InputTask): Promise<InputTaskResponse> {
        return apiClient.post<InputTaskResponse>('/input_task', inputTask);
    }
};
