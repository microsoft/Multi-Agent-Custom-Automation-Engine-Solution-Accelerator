
import {
    Body1,
    Button,
    Card,
    Text,
} from "@fluentui/react-components";
import {
    Send20Regular,
    Person20Regular,
    Phone20Regular,
    ShoppingBag20Regular,
    DocumentEdit20Regular,
} from "@fluentui/react-icons";
import React, { useRef, useEffect } from "react";
import { useNavigate } from 'react-router-dom';
import "./../../styles/Chat.css"; // Assuming you have a CSS file for additional styles
import "./../../styles/HomeInput.css";
import { HomeInputProps, quickTasks, QuickTask } from "../../models/homeInput";
import { TaskService } from "../../services/TaskService";
import { NewTaskService } from "../../services/NewTaskService";


const HomeInput: React.FC<HomeInputProps> = ({
    onInputSubmit,
    onQuickTaskSelect,
}) => {
    const [inputValue, setInputValue] = React.useState("");
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const navigate = useNavigate();

    /**
     * Reset textarea to empty state
     */
    const resetTextarea = () => {
        setInputValue("");
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.focus();
        }
    };

    // Listen for new task reset events
    useEffect(() => {
        const cleanup = NewTaskService.addResetListener(resetTextarea);
        return cleanup;
    }, []);

    const handleSubmit = async () => {
        if (inputValue.trim()) {
            try {
                // Submit the input task using TaskService
                const response = await TaskService.submitInputTask(inputValue.trim());

                // Clear the input field
                setInputValue("");
                if (textareaRef.current) {
                    textareaRef.current.style.height = "auto";
                }

                // Navigate to the plan page using the plan_id from the response
                navigate(`/plan/${response.plan_id}`);

            } catch (error) {
                console.error('Failed to create task:', error);
                // You can add error handling here if needed
            }
        }
    };
    const handleQuickTaskClick = (task: QuickTask) => {
        // Copy task description to textarea
        setInputValue(task.description);

        // Focus on textarea
        if (textareaRef.current) {
            textareaRef.current.focus();
        }

        // Call the onQuickTaskSelect with the task description
        onQuickTaskSelect(task.description);
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    }, [inputValue]);

    return (

        <div className="home-input-container">
            <div className="home-input-content">
                <div className="home-input-center-content">
                    <div className="home-input-title-wrapper">
                        <Text className="home-input-title">How can I help?</Text>
                    </div>

                    <div className="home-input-input-section">
                        <div className="home-input-input-wrapper">
                            <textarea
                                ref={textareaRef}
                                className="home-input-input-field"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                placeholder="Describe what you'd like to do or use / to reference files, people, and more"
                                rows={1}
                            />
                            <Button
                                className="home-input-send-button"
                                onClick={handleSubmit}
                                disabled={!inputValue.trim()}
                                icon={<Send20Regular />}
                            />
                        </div>
                        <div className="home-input-ai-footer">
                            AI-generated content may be incorrect
                        </div>
                    </div>

                    <div className="home-input-quick-tasks-section">
                        <div className="home-input-quick-tasks-header">
                            <Text className="home-input-quick-tasks-title">Quick tasks</Text>
                        </div>
                        <div className="home-input-quick-tasks">                            {quickTasks.map((task) => (
                            <Card
                                key={task.id}
                                className="home-input-quick-task-card"
                                onClick={() => handleQuickTaskClick(task)}
                            >
                                <div className="home-input-card-content">
                                    <div className="home-input-card-icon">{task.icon}</div>
                                    <div className="home-input-card-text-content">
                                        <Text className="home-input-card-title">{task.title}</Text>
                                        <Text className="home-input-card-description">{task.description}</Text>
                                    </div>
                                </div>
                            </Card>
                        ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default HomeInput; 