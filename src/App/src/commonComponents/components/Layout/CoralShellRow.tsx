// coral.config/components/Layout/CoralShellRow.tsx
// Structural wrapper for main workspace layout (horizontal split)

import React from "react";

const CoralShellRow: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div
      style={{
        display: "flex",
        flex: 1,
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
};

export default CoralShellRow;