import React, { ReactNode } from "react";
import { Subtitle2 } from "@fluentui/react-components";
import { Link } from "react-router-dom";

interface PanelLeftToolbarProps {
  panelIcon?: ReactNode;
  panelTitle?: string | null;
  linkTo?: string;
  children?: ReactNode;
}

const PanelLeftToolbar: React.FC<PanelLeftToolbarProps> = ({
  panelIcon,
  panelTitle,
  linkTo,
  children,
}) => {
  const TitleContent = (
    <div
      className="panelTitle"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        flexShrink: 1,
        overflow: "hidden",
        minWidth: 0,
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
        <Subtitle2
          style={{
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {panelTitle}
        </Subtitle2>
      )}
    </div>
  );

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
      {(panelIcon || panelTitle) &&
        (linkTo ? (
          <Link
            to={linkTo}
            style={{
              textDecoration: "none",
              color: "inherit",
              display: "flex",
              alignItems: "center",
              minWidth: 0,
              flexShrink: 1,
            }}
          >
            {TitleContent}
          </Link>
        ) : (
          TitleContent
        ))}
      <div
        className="panelTools"
        style={{
          display: "flex",
          alignItems: "center",
          flexGrow: 1,
          justifyContent: "flex-end",
          minWidth: 0,
        }}
      >
        {children}
      </div>
    </div>
  );
};

export default PanelLeftToolbar;
