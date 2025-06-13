// PromptCard.tsx
import React from "react";
import { Card } from "@fluentui/react-components";
import { Body1, Body1Strong } from "@fluentui/react-components";

type PromptCardProps = {
  title: string;
  description: string;
  icon?: React.ReactNode;
  onClick?: () => void;
};

const PromptCard: React.FC<PromptCardProps> = ({
  title,
  description,
  icon,
  onClick,
}) => {
  return (
    <Card
      onClick={onClick}
      style={{
        flex: "1",
        display: "flex",
        flexDirection: "column",
        padding: "16px",
        backgroundColor: "var(--colorNeutralBackground3)",
        border: "1px solid var(--colorNeutralStroke2)",
        borderRadius: "8px",
        cursor: "pointer",
        boxShadow: "none",
        transition: "background-color 0.2s ease-in-out",
      }}
      onMouseOver={(e) =>
        (e.currentTarget.style.backgroundColor =
          "var(--colorNeutralBackground4Hover)")
      }
      onMouseOut={(e) =>
        (e.currentTarget.style.backgroundColor =
          "var(--colorNeutralBackground3)")
      }
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
