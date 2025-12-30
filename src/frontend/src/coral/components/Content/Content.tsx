import React, { ReactNode, ReactElement } from "react";
import PanelToolbar from "../Panels/PanelLeftToolbar.js"; // Import to identify toolbar

interface ContentProps {
    children?: ReactNode;
}

const Content: React.FC<ContentProps> = ({ children }) => {
    const childrenArray = React.Children.toArray(children) as ReactElement[];
    const toolbar = childrenArray.find(
        (child) => React.isValidElement(child) && child.type === PanelToolbar
    );
    const content = childrenArray.filter(
        (child) => !(React.isValidElement(child) && child.type === PanelToolbar)
    );

    return (
        <div
            className="content"
            style={{
                display: "flex",
                flex: "1",
                flexDirection: "column",
                height: "100%",
                boxSizing: "border-box",
                position: "relative",
                minWidth: '320px',

            }}
        >
            {toolbar && <div style={{ flexShrink: 0 }}>{toolbar}</div>}

            <div
                className="panelContent"
                style={{
                    display: "flex",
                    flexDirection: "column",
                    flex: 1,
                    width:'100%',

    
                    overflow: "hidden", // prevent double scrollbars
                    minHeight: 0, // allow child to shrink properly
                }}
            >
                {content}
            </div>
        </div>
    );
};

export default Content;
