export interface QuickTask {
    id: string;
    title: string;
    description: string;
    icon: React.ReactNode | string;
}

export interface HomeInputProps {
    onInputSubmit: (input: string) => void;
    onQuickTaskSelect: (taskDescription: string) => void;
    selectedTeam?: TeamConfig | null;
}

import { TeamConfig } from './Team';
