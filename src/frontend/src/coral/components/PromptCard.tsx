// PromptCard.tsx
import React from "react";
import { Card } from "@fluentui/react-components";
import { Body1, Body1Strong } from "@fluentui/react-components";

type PromptCardProps = {
  title: string;
  description: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean; 
};

const PromptCard: React.FC<PromptCardProps> = ({
  title,
  description,
  icon,
  onClick,
  disabled = false,
}) => {
  return (
    <Card
      onClick={!disabled ? onClick : undefined} 
      style={{
        flex: "1",
        display: "flex",
        flexDirection: "column",
        padding: "16px",
        backgroundColor: disabled
          ? "var(--colorNeutralBackgroundDisabled)"
          : "var(--colorNeutralBackground3)",
        border: "1px solid var(--colorNeutralStroke1)",
        borderRadius: "8px",
        cursor: disabled ? "not-allowed" : "pointer",
        boxShadow: "none",
        opacity: disabled ? 0.4 : 1, // 
        transition: "background-color 0.2s ease-in-out",
      }}
      // 🧠 Only apply hover if not disabled
      onMouseOver={(e: React.MouseEvent<HTMLDivElement>) => {
        if (!disabled) {
          e.currentTarget.style.backgroundColor =
            "var(--colorNeutralBackground3Hover)";
            e.currentTarget.style.border = "1px solid var(--colorNeutralStroke1)"; // subtle shadow on hover
        }
      }}
      onMouseOut={(e: React.MouseEvent<HTMLDivElement>) => {
        if (!disabled) {
          e.currentTarget.style.backgroundColor =
            "var(--colorNeutralBackground3)";
            e.currentTarget.style.border = "1px solid var(--colorNeutralStroke1)";
        }
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {icon && (
              <div
                style={{
                  fontSize: "20px",
                  color: "var(--colorBrandForeground1)",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                {icon}
              </div>
            )}
            <Body1Strong>{title}</Body1Strong>
          </div>
          <Body1 style={{ color: "var(--colorNeutralForeground3)" }}>
            {description}
          </Body1>
        </div>
      </div>
    </Card>
  );
};

export default PromptCard;
