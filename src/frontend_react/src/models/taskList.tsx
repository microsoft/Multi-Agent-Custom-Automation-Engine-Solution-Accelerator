export interface Task {
    id: string;
    name: string;
    status: 'inprogress' | 'completed';
    date?: string;
}

export interface TaskListProps {
    inProgressTasks: Task[];
    completedTasks: Task[];
    onTaskSelect: (taskId: string) => void;
    loading?: boolean;
    selectedTaskId?: string;
}