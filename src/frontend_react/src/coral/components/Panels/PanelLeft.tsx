import React, { useState, useEffect, ReactNode, ReactElement } from "react";
import PanelToolbar from "./PanelLeftToolbar.js"; // Import to identify toolbar

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

      // Re-enable text selection
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);

    // Disable text selection
    document.body.style.userSelect = "none";
  };

  const childrenArray = React.Children.toArray(children) as ReactElement[];
  const toolbar = childrenArray.find(
    (child) => React.isValidElement(child) && child.type === PanelToolbar
  );
  const content = childrenArray.filter(
    (child) => !(React.isValidElement(child) && child.type === PanelToolbar)
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
          overflowY: "auto",
        //   padding: "16px",
        }}
      >
        {content}
      </div>

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
