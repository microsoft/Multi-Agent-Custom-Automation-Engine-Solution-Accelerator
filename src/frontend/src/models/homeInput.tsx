import {
    Desktop20Regular,
    BookmarkMultiple20Regular,
    Search20Regular,
    Wrench20Regular,
    Person20Regular,
    Building20Regular,
    Document20Regular,
    Database20Regular,
    Code20Regular,
    Play20Regular,
    Shield20Regular,
    Globe20Regular,
    Clipboard20Regular,
    WindowConsole20Regular,
} from '@fluentui/react-icons';
export interface QuickTask {
    id: string;
    title: string;
    description: string;
    icon: React.ReactNode | string;
}

export interface HomeInputProps {
    selectedTeam?: TeamConfig | null;
}
export const iconMap: Record<string, React.ReactNode> = {
    // Task/Logo icons
    'Wrench': <Wrench20Regular />,
    'TestTube': <Clipboard20Regular />, // Fallback since TestTube20Regular doesn't exist
    'Terminal': <WindowConsole20Regular />,
    'MonitorCog': <Desktop20Regular />,
    'BookMarked': <BookmarkMultiple20Regular />,
    'Search': <Search20Regular />,
    'Robot': <Person20Regular />, // Fallback since Robot20Regular doesn't exist
    'Code': <Code20Regular />,
    'Play': <Play20Regular />,
    'Shield': <Shield20Regular />,
    'Globe': <Globe20Regular />,
    'Person': <Person20Regular />,
    'Database': <Database20Regular />,
    'Document': <Document20Regular />,
    'Building': <Building20Regular />,
    'Desktop': <Desktop20Regular />,

    // Default fallback
    '📋': <Clipboard20Regular />,
    'default': <Clipboard20Regular />,
};

import { TeamConfig } from './Team';
