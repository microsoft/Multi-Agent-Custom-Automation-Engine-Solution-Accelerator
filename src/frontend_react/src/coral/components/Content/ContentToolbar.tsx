import React, { ReactNode } from "react";
import { Body1Strong } from "@fluentui/react-components";

interface ContentToolbarProps {
  panelIcon?: ReactNode;
  panelTitle?: string | null;
  children?: ReactNode;
}

const ContentToolbar: React.FC<ContentToolbarProps> = ({
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
            flex: "1 1 auto",
            overflow: "hidden", // Ensure title section is contained
          }}
        >
          {panelIcon && (
            <div
              style={{
                flexShrink: 0, // Prevent the icon from shrinking
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
          gap: "0",
        }}
      >
        {children}
      </div>
    </div>
  );
};

export default ContentToolbar;
