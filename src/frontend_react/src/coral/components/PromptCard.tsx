// PromptCard.tsx
import React from "react";
import { Card } from "@fluentui/react-components";
import { Body1, Body1Strong } from "@fluentui/react-components";

type PromptCardProps = {
  title: string;
  description: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean; // ✅ New prop for disabling the card
};

const PromptCard: React.FC<PromptCardProps> = ({
  title,
  description,
  icon,
  onClick,
  disabled = false, // 🔧 Default is false (enabled)
}) => {
  return (
    <Card
      onClick={!disabled ? onClick : undefined} // 🚫 Block click if disabled
      style={{
        flex: "1",
        display: "flex",
        flexDirection: "column",
        padding: "16px",
        backgroundColor: disabled
          ? "var(--colorNeutralBackgroundDisabled)"
          : "var(--colorNeutralBackground3)",
        border: "1px solid var(--colorNeutralStroke2)",
        borderRadius: "8px",
        cursor: disabled ? "not-allowed" : "pointer",
        boxShadow: "none",
        opacity: disabled ? 0.4 : 1, // 🧼 Matches Fluent disabled visual
        transition: "background-color 0.2s ease-in-out",
      }}
      // 🧠 Only apply hover if not disabled
      onMouseOver={(e) => {
        if (!disabled) {
          e.currentTarget.style.backgroundColor =
            "var(--colorNeutralBackground4Hover)";
        }
      }}
      onMouseOut={(e) => {
        if (!disabled) {
          e.currentTarget.style.backgroundColor =
            "var(--colorNeutralBackground3)";
        }
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {icon && (
          <div
            style={{
              fontSize: "20px",
              color: "var(--colorBrandForeground1)",
              marginTop: "2px",
            }}
          >
            {icon}
          </div>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <Body1Strong>{title}</Body1Strong>
          <Body1 style={{ color: "var(--colorNeutralForeground3)" }}>
            {description}
          </Body1>
        </div>
      </div>
    </Card>
  );
};

export default PromptCard;
