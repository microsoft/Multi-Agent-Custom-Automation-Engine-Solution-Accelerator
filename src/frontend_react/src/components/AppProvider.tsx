import React from 'react';
import { ThemeProvider, createTheme, ITheme, initializeIcons } from '@fluentui/react';

// Initialize icons for FluentUI
initializeIcons();

interface AppProviderProps {
    children: React.ReactNode;
}

// Create a custom theme with brand colors for your application
const myTheme: ITheme = createTheme({
    palette: {
        themePrimary: '#643A61',
        themeLighterAlt: '#F2B8FF',
        themeLighter: '#CE85DA',
        themeLight: '#B26BB1',
        themeTertiary: '#9F5E9D',
        themeSecondary: '#8B5189',
        themeDarkAlt: '#774575',
        themeDark: '#643A61',
        themeDarker: '#512F4E',
        neutralLighterAlt: '#faf9f8',
        neutralLighter: '#f3f2f1',
        neutralLight: '#edebe9',
        neutralQuaternaryAlt: '#e1dfdd',
        neutralQuaternary: '#d0d0d0',
        neutralTertiaryAlt: '#c8c6c4',
        neutralTertiary: '#a19f9d',
        neutralSecondary: '#605e5c',
        neutralPrimaryAlt: '#3b3a39',
        neutralPrimary: '#323130',
        neutralDark: '#201f1e',
        black: '#000000',
        white: '#ffffff',
    }
});

/**
 * Provider component to initialize the Fluent UI theme provider
 */
const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
    return (
        <ThemeProvider theme={myTheme}>
            {children}
        </ThemeProvider>
    );
};

export default AppProvider;
