import React, {
  useState,
  useEffect,
  ReactNode,
  ReactElement,
  isValidElement,
} from "react";
import PanelToolbar from "./PanelLeftToolbar.js";
import PanelFooter from "./PanelFooter"; // 👈 new
import {
  Avatar,
  Body1,
  Body1Strong,
  Caption1,
} from "@fluentui/react-components";
import Human from "../../imports/human.png";

interface PanelLeftProps {
  panelWidth?: number;
  panelResize?: boolean;
  children?: ReactNode;
}

const PanelLeft: React.FC<PanelLeftProps> = ({
  panelWidth = 500,
  panelResize = true,
  children,
}) => {
  const [width, setWidth] = useState(panelWidth);
  const [isHandleHovered, setIsHandleHovered] = useState(false);

  useEffect(() => {
    setWidth(panelWidth);
  }, [panelWidth]);

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!panelResize) return;

    const startX = e.clientX;
    const startWidth = width;

    const onMouseMove = (moveEvent: MouseEvent) => {
      const newWidth = Math.min(
        500,
        Math.max(256, startWidth + (moveEvent.clientX - startX))
      );
      setWidth(newWidth);
    };

    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    document.body.style.userSelect = "none";
  };

  const childrenArray = React.Children.toArray(children) as ReactElement[];
  const toolbar = childrenArray.find(
    (child) => isValidElement(child) && child.type === PanelToolbar
  );
  const footer = childrenArray.find(
    (child) => isValidElement(child) && child.type === PanelFooter
  );
  const content = childrenArray.filter(
    (child) =>
      !(
        isValidElement(child) &&
        (child.type === PanelToolbar || child.type === PanelFooter)
      )
  );

  return (
    <div
      className="panelLeft"
      style={{
        width: `${width}px`,
        display: "flex",
        flexDirection: "column",
        backgroundColor: "var(--colorNeutralBackground4)",
        height: "100%",
        boxSizing: "border-box",
        position: "relative",
        borderRight: panelResize
          ? isHandleHovered
            ? "2px solid var(--colorNeutralStroke2)"
            : "2px solid transparent"
          : "none",
      }}
    >
      {toolbar && <div style={{ flexShrink: 0 }}>{toolbar}</div>}

      <div
        className="panelContent"
        style={{
          flex: 1,
          overflowY: "hidden", /* Remove scrollbar from container - only scroll within individual sections */
          overflowX: "hidden",
          boxSizing: "border-box",
        }}
      >
        {content}
      </div>

      {footer && <div>{footer}</div>}

      {panelResize && (
        <div
          className="resizeHandle"
          onMouseDown={handleMouseDown}
          onMouseEnter={() => setIsHandleHovered(true)}
          onMouseLeave={() => setIsHandleHovered(false)}
          style={{
            position: "absolute",
            top: 0,
            right: 0,
            width: "2px",
            height: "100%",
            cursor: "ew-resize",
            zIndex: 1,
            backgroundColor: isHandleHovered
              ? "var(--colorNeutralStroke2)"
              : "transparent",
          }}
        />
      )}
    </div>
  );
};

export default PanelLeft;
