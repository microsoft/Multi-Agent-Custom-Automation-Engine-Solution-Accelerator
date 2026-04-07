export interface Task {
    id: string;
    name: string;
    status: string;
    date?: string;
}

export interface TaskListProps {
    completedTasks: Task[];
    onTaskSelect: (taskId: string) => void;
    loading?: boolean;
    selectedTaskId?: string;
    isLoadingTeam?: boolean;
}