
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
import "./../../styles/Chat.css"; // Assuming you have a CSS file for additional styles
import "./../../styles/HomeInput.css";
import { HomeInputProps, quickTasks } from "../../models/homeInput";


const HomeInput: React.FC<HomeInputProps> = ({
    onInputSubmit,
    onQuickTaskSelect,
}) => {
    const [inputValue, setInputValue] = React.useState("");
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const handleSubmit = () => {
        if (inputValue.trim()) {
            onInputSubmit(inputValue.trim());
            setInputValue("");
            if (textareaRef.current) {
                textareaRef.current.style.height = "auto";
            }
        }
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

    return (<div className="home-input-container">
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
                            onKeyPress={handleKeyPress}
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
                        <Button appearance="transparent" className="home-input-refresh-button">
                            Refresh
                        </Button>
                    </div>
                    <div className="home-input-quick-tasks">
                        {quickTasks.map((task) => (
                            <Card
                                key={task.id}
                                className="home-input-quick-task-card"
                                onClick={() => onQuickTaskSelect(task.id)}
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