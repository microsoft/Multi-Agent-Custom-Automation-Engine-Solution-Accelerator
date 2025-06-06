import React from 'react';
import { FluentProvider, teamsLightTheme } from '@fluentui/react-components';

interface AppProviderProps {
    children: React.ReactNode;
}

/**
 * Provider component to initialize the Fluent UI theme provider
 */
const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
    return (
        <FluentProvider theme={teamsLightTheme}>
            {children}
        </FluentProvider>
    );
};

export default AppProvider;
