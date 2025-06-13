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
    processingSubtaskId: string | null;
    OnApproveStep: (step: Step) => void;
    OnRejectStep: (step: Step) => void;
}