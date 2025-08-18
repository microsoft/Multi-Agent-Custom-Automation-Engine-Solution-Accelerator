import {
    Body1Strong,
    Button,
    Caption1,
    Title2,
} from "@fluentui/react-components";
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
import React, { useRef, useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

import "./../../styles/Chat.css";
import "../../styles/prism-material-oceanic.css";
import "./../../styles/HomeInput.css";

import { HomeInputProps, QuickTask } from "../../models/homeInput";
import { TeamConfig } from "../../models/Team";
import { TaskService } from "../../services/TaskService";
import { NewTaskService } from "../../services/NewTaskService";
import { RAIErrorCard, RAIErrorData } from "../errors";

import ChatInput from "@/coral/modules/ChatInput";
import InlineToaster, { useInlineToaster } from "../toast/InlineToaster";
import PromptCard from "@/coral/components/PromptCard";
import { Send } from "@/coral/imports/bundleicons";

// Icon mapping function to convert string icons to FluentUI icons
const getIconFromString = (iconString: string | React.ReactNode): React.ReactNode => {
    // If it's already a React node, return it
    if (typeof iconString !== 'string') {
        return iconString;
    }

    const iconMap: Record<string, React.ReactNode> = {
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

    return iconMap[iconString] || iconMap['default'] || <Clipboard20Regular />;
};

const HomeInput: React.FC<HomeInputProps> = ({
    onInputSubmit,
    onQuickTaskSelect,
    selectedTeam,
}) => {
    const [submitting, setSubmitting] = useState(false);
    const [input, setInput] = useState("");
    const [raiError, setRAIError] = useState<RAIErrorData | null>(null);

    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const navigate = useNavigate();
    const location = useLocation(); // ✅ location.state used to control focus
    const { showToast, dismissToast } = useInlineToaster();

    useEffect(() => {
        if (location.state?.focusInput) {
            textareaRef.current?.focus();
        }
    }, [location]);

    const resetTextarea = () => {
        setInput("");
        setRAIError(null); // Clear any RAI errors
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.focus();
        }
    };

    useEffect(() => {
        const cleanup = NewTaskService.addResetListener(resetTextarea);
        return cleanup;
    }, []);

    const handleSubmit = async () => {
        if (input.trim()) {
            setSubmitting(true);
            setRAIError(null); // Clear any previous RAI errors
            let id = showToast("Creating a plan", "progress");

            try {
                const response = await TaskService.createPlan(
                    input.trim(),
                    selectedTeam?.team_id
                );
                setInput("");

                if (textareaRef.current) {
                    textareaRef.current.style.height = "auto";
                }

                if (response.plan_id && response.plan_id !== null) {
                    showToast("Plan created!", "success");
                    dismissToast(id);

                    // Navigate to create page (no team ID in URL anymore)
                    console.log('HomeInput: Navigating to plan creation with team:', selectedTeam?.name);
                    navigate(`/plan/${response.plan_id}`);
                } else {
                    showToast("Failed to create plan", "error");
                    dismissToast(id);
                }
            } catch (error: any) {
                dismissToast(id);

                // Check if this is an RAI validation error
                let errorDetail = null;
                try {
                    // Try to parse the error detail if it's a string
                    if (typeof error?.response?.data?.detail === 'string') {
                        errorDetail = JSON.parse(error.response.data.detail);
                    } else {
                        errorDetail = error?.response?.data?.detail;
                    }
                } catch (parseError) {
                    // If parsing fails, use the original error
                    errorDetail = error?.response?.data?.detail;
                }

                // Handle RAI validation errors with better UX
                if (errorDetail?.error_type === 'RAI_VALIDATION_FAILED') {
                    setRAIError(errorDetail);
                } else {
                    // Handle other errors with toast messages
                    const errorMessage = errorDetail?.description ||
                        errorDetail?.message ||
                        error?.response?.data?.message ||
                        error?.message ||
                        "Something went wrong";
                    showToast(errorMessage, "error");
                }

            } finally {
                setInput("");
                setSubmitting(false);
            }
        }
    };

    const handleQuickTaskClick = (task: QuickTask) => {
        setInput(task.description);
        setRAIError(null); // Clear any RAI errors when selecting a quick task
        if (textareaRef.current) {
            textareaRef.current.focus();
        }
        onQuickTaskSelect(task.description);
    };

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    }, [input]);

    // Convert team starting_tasks to QuickTask format
    const tasksToDisplay: QuickTask[] = selectedTeam && selectedTeam.starting_tasks ?
        selectedTeam.starting_tasks.map((task, index) => {
            // Handle both string tasks and StartingTask objects
            if (typeof task === 'string') {
                return {
                    id: `team-task-${index}`,
                    title: task,
                    description: task,
                    icon: getIconFromString("📋")
                };
            } else {
                // Handle StartingTask objects
                const startingTask = task as any; // Type assertion for now
                return {
                    id: startingTask.id || `team-task-${index}`,
                    title: startingTask.name || startingTask.prompt || 'Task',
                    description: startingTask.prompt || startingTask.name || 'Task description',
                    icon: getIconFromString(startingTask.logo || "📋")
                };
            }
        }) : [];

    return (
        <div className="home-input-container">
            <div className="home-input-content">
                <div className="home-input-center-content">
                    <div className="home-input-title-wrapper">
                        <Title2>How can I help?</Title2>
                    </div>

                    {/* Show RAI error if present */}
                    {raiError && (
                        <RAIErrorCard
                            error={raiError}
                            onRetry={() => {
                                setRAIError(null);
                                if (textareaRef.current) {
                                    textareaRef.current.focus();
                                }
                            }}
                            onDismiss={() => setRAIError(null)}
                        />
                    )}

                    <ChatInput
                        ref={textareaRef} // forwarding
                        value={input}
                        placeholder="Tell us what needs planning, building, or connecting—we'll handle the rest."
                        onChange={setInput}
                        onEnter={handleSubmit}
                        disabledChat={submitting}
                    >
                        <Button
                            appearance="subtle"
                            className="home-input-send-button"
                            onClick={handleSubmit}
                            disabled={submitting}
                            icon={<Send />}
                        />
                    </ChatInput>

                    <InlineToaster />

                    <div className="home-input-quick-tasks-section">
                        {tasksToDisplay.length > 0 && (
                            <>
                                <div className="home-input-quick-tasks-header">
                                    <Body1Strong>Quick tasks</Body1Strong>
                                </div>

                                <div className="home-input-quick-tasks">
                                    {tasksToDisplay.map((task) => (
                                        <PromptCard
                                            key={task.id}
                                            title={task.title}
                                            icon={task.icon}
                                            description={task.description}
                                            onClick={() => handleQuickTaskClick(task)}
                                            disabled={submitting}
                                        />
                                    ))}
                                </div>
                            </>
                        )}
                        {tasksToDisplay.length === 0 && selectedTeam && (
                            <div style={{
                                textAlign: 'center',
                                padding: '32px 16px',
                                color: '#666'
                            }}>
                                <Caption1>No starting tasks available for this team</Caption1>
                            </div>
                        )}
                        {!selectedTeam && (
                            <div style={{
                                textAlign: 'center',
                                padding: '32px 16px',
                                color: '#666'
                            }}>
                                <Caption1>Select a team to see available tasks</Caption1>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default HomeInput;
