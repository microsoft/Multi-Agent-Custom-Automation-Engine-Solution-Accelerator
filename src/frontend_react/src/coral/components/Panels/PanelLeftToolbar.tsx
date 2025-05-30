import React, { ReactNode } from "react";
import { Body1Strong } from "@fluentui/react-components";

interface PanelLeftToolbarProps {
  panelIcon?: ReactNode;
  panelTitle?: string | null;
  children?: ReactNode;
}

const PanelLeftToolbar: React.FC<PanelLeftToolbarProps> = ({
  panelIcon,
  panelTitle,
  children,
}) => {
  return (
    <div
      className="panelToolbar"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        padding: "16px",
        boxSizing: "border-box",
        height: "56px",
      }}
    >
      {(panelIcon || panelTitle) && (
        <div
          className="panelTitle"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            flexShrink: 1, // Allow shrinking when needed
            overflow: "hidden",
            minWidth: 0, // Prevents breaking layout when shrinking
          }}
        >
          {panelIcon && (
            <div
              style={{
                flexShrink: 0, // Prevents icon from shrinking
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
      )}
      <div
        className="panelTools"
        style={{
          display: "flex",
          alignItems: "center",
 
          flexGrow: 1, // Allows `panelTools` to take the remaining space
          justifyContent: "flex-end", // Makes sure buttons hug their content
          minWidth: 0, // Prevents layout breaking when content shrinks
        }}
      >
        {children}
      </div>
    </div>
  );
};

export default PanelLeftToolbar;
