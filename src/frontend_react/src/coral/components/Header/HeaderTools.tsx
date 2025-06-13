import React, { useState } from "react";
import { Toolbar, ToolbarDivider, Avatar } from "@fluentui/react-components";
import eventBus from "../eventbus";
import PanelRightToggles from "./PanelRightToggles"; // Import PanelRightToggles


interface HeaderToolsProps {
    children?: React.ReactNode;
}

const HeaderTools: React.FC<HeaderToolsProps> = ({ children }) => {


    return (
        <Toolbar
            style={{
                display: "flex",
                flex: "0",
                alignItems: "center",
                flexDirection: "row-reverse",
                padding: "4px 0",
            }}
        >
            {children}
        </Toolbar>
    );
};

export default HeaderTools;
