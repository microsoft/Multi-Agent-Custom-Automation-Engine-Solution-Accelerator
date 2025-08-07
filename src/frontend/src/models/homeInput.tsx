import { DocumentEdit20Regular, Person20Regular, Phone20Regular, ShoppingBag20Regular } from "@fluentui/react-icons";

export interface QuickTask {
    id: string;
    title: string;
    description: string;
    icon: React.ReactNode;
}

export const quickTasks: QuickTask[] = [
    {
        id: "onboard",
        title: "Onboard employee",
        description: "Onboard a new employee, Jessica Smith.",
        icon: <Person20Regular />,
    },
    {
        id: "mobile",
        title: "Mobile plan query",
        description: "Ask about roaming plans prior to heading overseas.",
        icon: <Phone20Regular />,
    },
    {
        id: "addon",
        title: "Buy add-on",
        description: "Enable roaming on mobile plan, starting next week.",
        icon: <ShoppingBag20Regular />,
    },
    {
        id: "press",
        title: "Draft a press release",
        description: "Write a press release about our current products.",
        icon: <DocumentEdit20Regular />,
    },
];

export interface HomeInputProps {
    onInputSubmit: (input: string) => void;
    onQuickTaskSelect: (taskDescription: string) => void;
    selectedTeam?: TeamConfig | null;
}

import { TeamConfig } from './Team';
