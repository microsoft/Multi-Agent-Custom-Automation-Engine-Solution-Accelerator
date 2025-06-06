import React, { useRef, useState, useEffect } from "react";
import {
    Tag,
    Tooltip as FluentTooltip,
    Caption1,
} from "@fluentui/react-components";
import HeaderTools from "../components/Header/HeaderTools";

interface ChatInputProps {
    value: string;
    onChange: (val: string) => void;
    onEnter?: () => void;
    placeholder?: string;
    children?: React.ReactNode;
}

const ChatInput: React.FC<ChatInputProps> = ({
    value,
    onChange,
    onEnter,
    placeholder = "Type a message...",
    children,
}) => {
    const [isFocused, setIsFocused] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const inputContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    }, [value]);

    return (
        <div
            style={{
                width: "100%",

                margin: "0 auto",
            }}
        >
            <div
                ref={inputContainerRef}
                style={{
                    //   margin: "0 16px 16px 16px",
                    display: "inline-flex",
                    flexDirection: "column",
                    gap: "8px",
                    alignItems: "stretch",
                    width: "100%",
                    padding: "8px",
                    borderRadius: "var(--borderRadiusLarge)",
                    backgroundColor: "var(--colorNeutralBackground1)",
                    // border: "1px solid",
                    borderColor: isFocused
                        ? "var(--colorNeutralStroke1Pressed)"
                        : "var(--colorNeutralStroke1)",
                    transition: "border-color 0.2s ease-in-out",
                    position: "relative",
                    boxSizing: "border-box",
                    overflow:'hidden'
                }}
            >
                <textarea
                    ref={textareaRef}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            onEnter?.();
                        }
                    }}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    placeholder={placeholder}
                    rows={1}
                    style={{
                        resize: "none",
                        overflowY: "scroll",
                        height: "auto",
                        minHeight: "24px",
                        maxHeight: "150px",
                        padding: "8px",
                        backgroundColor: "transparent",
                        border: "none",
                        outline: "none",
                        fontFamily: "var(--fontFamilyBase)",
                        fontSize: "var(--fontSizeBase300)",
                        fontWeight: "var(--fontWeightRegular)",
                        color: "var(--colorNeutralForeground1)",
                        lineHeight: 1.5,
                        boxSizing: "border-box",
                    }}
                />

                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        maxHeight: "32px",
                    }}
                >
                    <FluentTooltip content="AI-generated content may be incorrect." relationship="label">
                        <Tag appearance="filled" size="small">
                            AI Generated
                        </Tag>
                    </FluentTooltip>

                    <HeaderTools>
                        {children}
                    </HeaderTools>
                </div>

                <span
                    style={{
                        position: "absolute",
                        bottom: 0,
                        left: 0,
                        width: "100%",
                        height: "2px",
                        backgroundColor: "var(--colorCompoundBrandStroke)",
                        transform: isFocused ? "scaleX(1)" : "scaleX(0)",
                        transition: "transform 0.2s ease-in-out",
                        textAlign: "center",
                    }}
                />
            </div>
            <br />
            <div
                            style={{
                    color: "var(--colorNeutralForeground3)",
                    marginTop: "8px",
                    paddingBottom: "8px",
                    textAlign: "center",
                }}>
            <Caption1

            >
                AI-Generated content may be incorrect
            </Caption1>
            </div>

        </div>
    );
};

export default ChatInput;
