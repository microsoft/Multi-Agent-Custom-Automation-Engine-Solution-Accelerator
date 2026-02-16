import React from "react";

const CoralAccordionPanel: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  return (
    <div style={{ margin: "8px", maxHeight: 280, overflowY: "auto" }}>
      {children}
    </div>
  );
};
CoralAccordionPanel.displayName = "CoralAccordionPanel";
export default CoralAccordionPanel;
