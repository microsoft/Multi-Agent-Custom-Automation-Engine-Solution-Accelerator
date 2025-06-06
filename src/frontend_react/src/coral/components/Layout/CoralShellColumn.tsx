// coral.config/components/Layout/CoralShellColumn.tsx
// Structural wrapper for top-level app layout (vertical orientation)

import React from "react";

const CoralShellColumn: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
        backgroundColor: "var(--colorNeutralBackground3)",
      }}
    >
      {children}
    </div>
  );
};

export default CoralShellColumn;



