import React, { ReactNode } from "react";
import { Subtitle2 } from "@fluentui/react-components";
import { Link } from "react-router-dom";
import "../../../styles/Panel.css";

interface PanelLeftToolbarProps {
  panelIcon?: ReactNode;
  panelTitle?: string | null;
  linkTo?: string;
  onTitleClick?: () => void;
  children?: ReactNode;
}

const PanelLeftToolbar: React.FC<PanelLeftToolbarProps> = ({
  panelIcon,
  panelTitle,
  linkTo,
  onTitleClick,
  children,
}) => {
  const TitleContent = (
    <div className="panel-title">
      {panelIcon && (
        <div className="panel-title-icon">
          {panelIcon}
        </div>
      )}
      {panelTitle && (
        <Subtitle2 className="panel-title-text">
          {panelTitle}
        </Subtitle2>
      )}
    </div>
  );

  return (
    <div className="panel-toolbar">
      {(panelIcon || panelTitle) &&
        (onTitleClick ? (
          <div
            onClick={onTitleClick}
            className="panel-title-clickable clickable-element"
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onTitleClick();
              }
            }}
          >
            {TitleContent}
          </div>
        ) : linkTo ? (
          <Link
            to={linkTo}
            className="panel-title-clickable"
          >
            {TitleContent}
          </Link>
        ) : (
          TitleContent
        ))}
      <div className="panel-tools">
        {children}
      </div>
    </div>
  );
};

export default PanelLeftToolbar;
