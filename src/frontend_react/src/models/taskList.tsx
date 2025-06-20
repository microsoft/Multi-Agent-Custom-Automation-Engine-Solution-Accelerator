export interface Task {
    id: string;
    name: string;
    status: 'inprogress' | 'completed';
    date?: string;
    completed_steps?: number;
    total_steps?: number;
}

export interface TaskListProps {
    inProgressTasks: Task[];
    completedTasks: Task[];
    onTaskSelect: (taskId: string) => void;
    loading?: boolean;
    selectedTaskId?: string;
}