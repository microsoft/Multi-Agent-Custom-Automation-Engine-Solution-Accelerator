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

import { HomeInputProps, quickTasks, QuickTask } from "../../models/homeInput";
import { TaskService } from "../../services/TaskService";
import { NewTaskService } from "../../services/NewTaskService";

import ChatInput from "@/coral/modules/ChatInput";
import InlineToaster, { useInlineToaster } from "../toast/InlineToaster";
import PromptCard from "@/coral/components/PromptCard";
import { Send } from "@/coral/imports/bundleicons";

const HomeInput: React.FC<HomeInputProps> = ({
    onInputSubmit,
    onQuickTaskSelect,
}) => {
    const [submitting, setSubmitting] = useState(false);
    const [input, setInput] = useState("");

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
            let id = showToast("Creating a plan", "progress");

            try {
                const response = await TaskService.submitInputTask(input.trim());
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
            } catch (error:any) {
                dismissToast(id);
                showToast(JSON.parse(error?.message)?.detail, "error");
            } finally {
                setInput("");
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
                                    disabled={submitting}
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
