import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Button,
    Spinner,
    Toast,
    ToastTitle,
    ToastBody,
    useToastController,
    Toaster
} from '@fluentui/react-components';
import {
    Add20Regular,
    ErrorCircle20Regular
} from '@fluentui/react-icons';
import '../styles/PlanPage.css';
import CoralShellColumn from '../coral/components/Layout/CoralShellColumn';
import CoralShellRow from '../coral/components/Layout/CoralShellRow';
import Content from '../coral/components/Content/Content';
import PanelLeft from '../coral/components/Panels/PanelLeft';
import PanelLeftToolbar from '../coral/components/Panels/PanelLeftToolbar';
import TaskList from '../components/content/TaskList';
import { Task } from '../models/taskList';
import { TaskService } from '../services/TaskService';
import { apiService } from '../api/apiService';
import { PlanWithSteps } from '../models';
import HomeInput from '@/components/content/HomeInput';
import { NewTaskService } from '../services/NewTaskService';
import PlanPanelLeft from '@/components/content/PlanPanelLeft';

/**
 * HomePage component - displays task lists and provides navigation
 * Accessible via the route "/"
 */
const HomePage: React.FC = () => {
    /**
    * Handle new task creation from the "New task" button
    * Resets textarea to empty state on HomePage
    */
    const handleNewTaskButton = useCallback(() => {
        NewTaskService.handleNewTaskFromHome();
    }, []);

    /**
     * Handle new task creation from input submission - placeholder for future implementation
     */
    const handleNewTask = useCallback((taskName: string) => {
        console.log('Creating new task:', taskName);
    }, []);

    return (
        <>
            <Toaster toasterId="toast" />
            <CoralShellColumn>
                <CoralShellRow>
                    <PlanPanelLeft
                        onNewTaskButton={handleNewTaskButton}
                    />
                    <Content>
                        <HomeInput
                            onInputSubmit={handleNewTask}
                            onQuickTaskSelect={handleNewTask}
                        />
                    </Content>

                </CoralShellRow>
            </CoralShellColumn>
        </>
    );
};

export default HomePage;