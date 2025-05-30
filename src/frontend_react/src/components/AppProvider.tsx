import React from 'react';
import { ThemeProvider, createTheme, ITheme, initializeIcons } from '@fluentui/react';

// Initialize icons for FluentUI
initializeIcons();

interface AppProviderProps {
    children: React.ReactNode;
}

// Create a custom theme with brand colors for your application


/**
 * Provider component to initialize the Fluent UI theme provider
 */
const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
    return (
        <ThemeProvider>
            {children}
        </ThemeProvider>
    );
};

export default AppProvider;
