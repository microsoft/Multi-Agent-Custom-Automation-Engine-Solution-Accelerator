import React from "react";

const PanelFooter: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div
      style={{
        padding: "24px 16px",
        width:'100%'
      }}
    >
      {children}
    </div>
  );
};

PanelFooter.displayName = "PanelFooter";

export default PanelFooter;
