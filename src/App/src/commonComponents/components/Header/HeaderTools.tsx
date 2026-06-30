import React from "react";
import { Toolbar } from "@fluentui/react-components";

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
