import { ProcessedPlanData, Step } from "./plan";

export interface SubTask {
    id: string;
    name: string;
    status: 'completed' | 'working' | 'removed';
}

export interface Agent {
    id: string;
    name: string;
    description: string;
    avatarUrl?: string;
}

export interface Human {
    id: string;
    name: string;
    email: string;
    avatarUrl?: string;
}

export interface TaskDetailsProps {
    planData: ProcessedPlanData;
    loading: boolean;
    submittingChatDisableInput: boolean;
    processingSubtaskId: string | null;
    OnApproveStep: (step: Step, total: number, completed: number, approve: boolean) => void;
}