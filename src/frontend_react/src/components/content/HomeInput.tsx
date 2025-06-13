import {
    Body1,
    Body1Strong,
    Button,
    Caption1,
    Card,
    Title2,
} from "@fluentui/react-components";
import { FoodToast20Regular, Send20Regular } from "@fluentui/react-icons";
import React, { useRef, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import "./../../styles/Chat.css";
import "../../styles/prism-material-oceanic.css";
import "./../../styles/HomeInput.css";
import { HomeInputProps, quickTasks, QuickTask } from "../../models/homeInput";
import { TaskService } from "../../services/TaskService";
import { NewTaskService } from "../../services/NewTaskService";
import ChatInput from "@/coral/modules/ChatInput";
import InlineToaster, { useInlineToaster } from "../toast/InlineToaster";
import PromptCard from "@/coral/components/PromptCard";

const HomeInput: React.FC<HomeInputProps> = ({
    onInputSubmit,
    onQuickTaskSelect,
}) => {
    const [submitting, setSubmitting] = useState(false);
    const [input, setInput] = useState("");
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const navigate = useNavigate();
    const { showToast } = useInlineToaster();

    const resetTextarea = () => {
        setInput("");
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
            showToast("Creating a plan..", "progress");
            try {
                const response = await TaskService.submitInputTask(input.trim());

                setInput("");
                if (textareaRef.current) {
                    textareaRef.current.style.height = "auto";
                }

                showToast("Plan created!", "success");
                navigate(`/plan/${response.plan_id}`);
                console.log('Task response', response);
                if (response.plan_id != null) {
                    // plan_id is valid (not null or undefined)
                    navigate(`/plan/${response.plan_id}`);
                } else {
                    // plan_id is not valid, handle accordingly
                    console.log('Invalid plan:', response.status);
                    showToast("Failed to create plan", "error");
                }
            } catch (error) {
                console.error("Failed to create plan:", error);
                showToast("Something went wrong", "error");
            } finally {
                setSubmitting(false);
            }
        }
    };

    const handleQuickTaskClick = (task: QuickTask) => {
        setInput(task.description);
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



    return (
        <div className="home-input-container">
            <div className="home-input-content">
                <div className="home-input-center-content">
                    <div className="home-input-title-wrapper">
                        <Title2>How can I help?</Title2>
                    </div>

                    <ChatInput
                        value={input}
                        placeholder="Tell us what needs planning, building, or connecting—we'll handle the rest."
                        onChange={setInput}
                        disabledChat={submitting}
                    >
                        <Button
                            appearance="subtle"
                            className="home-input-send-button"
                            onClick={handleSubmit}
                            disabled={submitting}
                            icon={<Send20Regular />}
                        />

                    </ChatInput>

                    {/* Inline Toaster lives right under chat input */}
                    <InlineToaster />

                    <div className="home-input-quick-tasks-section">
                        <div className="home-input-quick-tasks-header">
                            <Body1Strong>Quick tasks</Body1Strong>
                        </div>
                        <div className="home-input-quick-tasks">
                            {quickTasks.map((task) => (
                                <PromptCard
                                    key={task.id}
                                    title={task.title}
                                    icon={task.icon}
                                    description={task.description}
                                    onClick={() => handleQuickTaskClick(task)}
                                />
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default HomeInput;
