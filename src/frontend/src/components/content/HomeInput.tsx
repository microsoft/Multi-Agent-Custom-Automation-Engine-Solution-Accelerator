import {
    Body1Strong,
    Button,
    Caption1,
    Title2,
} from "@fluentui/react-components";

import React, { useRef, useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

import "./../../styles/Chat.css";
import "../../styles/prism-material-oceanic.css";
import "./../../styles/HomeInput.css";

import { HomeInputProps, iconMap, QuickTask } from "../../models/homeInput";
import { TaskService } from "../../services/TaskService";
import { NewTaskService } from "../../services/NewTaskService";
import { RAIErrorCard, RAIErrorData } from "../errors";

import ChatInput from "@/coral/modules/ChatInput";
import InlineToaster, { useInlineToaster } from "../toast/InlineToaster";
import PromptCard from "@/coral/components/PromptCard";
import { Send } from "@/coral/imports/bundleicons";
import { Clipboard20Regular } from "@fluentui/react-icons";

// Icon mapping function to convert string icons to FluentUI icons
const getIconFromString = (iconString: string | React.ReactNode): React.ReactNode => {
    // If it's already a React node, return it
    if (typeof iconString !== 'string') {
        return iconString;
    }

    return iconMap[iconString] || iconMap['default'] || <Clipboard20Regular />;
};

const truncateDescription = (description: string, maxLength: number = 180): string => {
    if (!description) return '';

    if (description.length <= maxLength) {
        return description;
    }


    const truncated = description.substring(0, maxLength);
    const lastSpaceIndex = truncated.lastIndexOf(' ');

    const cutPoint = lastSpaceIndex > maxLength - 20 ? lastSpaceIndex : maxLength;

    return description.substring(0, cutPoint) + '...';
};

// Extended QuickTask interface to store both truncated and full descriptions
interface ExtendedQuickTask extends QuickTask {
    fullDescription: string; // Store the full, untruncated description
}

const HomeInput: React.FC<HomeInputProps> = ({
    selectedTeam,
}) => {
    const [submitting, setSubmitting] = useState<boolean>(false);
    const [input, setInput] = useState<string>("");
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
                console.log("Plan created:", response);
                setInput("");

                if (textareaRef.current) {
                    textareaRef.current.style.height = "auto";
                }

                if (response.plan_id && response.plan_id !== null) {
                    showToast("Plan created!", "success");
                    dismissToast(id);

                    navigate(`/plan/${response.plan_id}`);
                } else {
                    showToast("Failed to create plan", "error");
                    dismissToast(id);
                }
            } catch (error: any) {
                console.log("Error creating plan:", error);
                let errorMessage = "Unable to create plan. Please try again.";
                dismissToast(id);
                // Check if this is an RAI validation error
                try {
                    // errorDetail = JSON.parse(error);
                    errorMessage = error?.message || errorMessage;
                } catch (parseError) {
                    console.error("Error parsing error detail:", parseError);
                }


                showToast(errorMessage, "error");
            } finally {
                setInput("");
                setSubmitting(false);
            }
        }
    };

    const handleQuickTaskClick = (task: ExtendedQuickTask) => {
        setInput(task.fullDescription);
        setRAIError(null); // Clear any RAI errors when selecting a quick task
        if (textareaRef.current) {
            textareaRef.current.focus();
        }
    };

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    }, [input]);

    // Convert team starting_tasks to ExtendedQuickTask format
    const tasksToDisplay: ExtendedQuickTask[] = selectedTeam && selectedTeam.starting_tasks ?
        selectedTeam.starting_tasks.map((task, index) => {
            // Handle both string tasks and StartingTask objects
            if (typeof task === 'string') {
                return {
                    id: `team-task-${index}`,
                    title: task,
                    description: truncateDescription(task),
                    fullDescription: task, // Store the full description
                    icon: getIconFromString("📋")
                };
            } else {
                // Handle StartingTask objects
                const startingTask = task as any; // Type assertion for now
                const taskDescription = startingTask.prompt || startingTask.name || 'Task description';
                return {
                    id: startingTask.id || `team-task-${index}`,
                    title: startingTask.name || startingTask.prompt || 'Task',
                    description: truncateDescription(taskDescription),
                    fullDescription: taskDescription, // Store the full description
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
                    {/* {raiError && (
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
                    )} */}

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
                                    <div>
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