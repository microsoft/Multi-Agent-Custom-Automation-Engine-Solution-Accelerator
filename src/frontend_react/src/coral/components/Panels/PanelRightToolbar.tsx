import React, { ReactNode } from "react";
import { Body1Strong, Button } from "@fluentui/react-components";
import eventBus from "../eventbus.js";
import { Dismiss } from "../../imports/bundleicons.js";

interface PanelRightToolbarProps {
    panelTitle?: string | null;
    panelIcon?: ReactNode;
    //   panelType?: "first" | "second"; // Optional, defaults to "first"
    children?: ReactNode;
    handleDismiss?: () => void;  // Add this line
}

const PanelRightToolbar: React.FC<PanelRightToolbarProps> = ({
    panelTitle,
    panelIcon,
    //   panelType = "first", // Default value set here
    children,
}) => {
    const handleDismiss = () => {
        eventBus.emit("setActivePanel", null); // Close the current panel
    };

    return (
        <div
            className="panelToolbar"
            style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "16px",
                boxSizing: "border-box",
                height: "56px",
                gap: "8px",
            }}
        >
            <div
                className="panelTitle"
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    flex: "1 1 auto",
                    overflow: "hidden",
                }}
            >
                {panelIcon && (
                    <div
                        style={{
                            flexShrink: 0,
                            display: "flex",
                            alignItems: "center",
                        }}
                    >
                        {panelIcon}
                    </div>
                )}
                {panelTitle && (
                    <Body1Strong
                        style={{
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                        }}
                    >
                        {panelTitle}
                    </Body1Strong>
                )}
            </div>
            <div
                className="panelTools"
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0px",
                }}
            >
                {children}
                <Button
                    appearance="subtle"
                    icon={<Dismiss />}
                    onClick={handleDismiss} // Handle dismiss logic
                    aria-label="Close panel"
                />
            </div>
        </div>
    );
};

export default PanelRightToolbar;