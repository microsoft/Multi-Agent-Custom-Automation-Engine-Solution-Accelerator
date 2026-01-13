import React from "react";
import {
  Avatar,
  AvatarProps,
  Body1Strong,
  Caption1,
} from "@fluentui/react-components";

interface PanelUserCardProps extends AvatarProps {
  name: string;       // required for both Avatar and label
  alias?: string;     // optional sub-label
}

const PanelUserCard: React.FC<PanelUserCardProps> = ({ name, alias, ...avatarProps }) => {
  return (
    <div
      style={{
        display: "flex",
        gap: "12px",
        alignItems: "center",
      }}
    >
      <Avatar
        name={name}
        {...avatarProps}
      />
      <div style={{ display: "flex", flexDirection: "column" }}>
        <Body1Strong>{name}</Body1Strong>
        {alias && (
          <Caption1 style={{ color: "var(--colorNeutralForeground3)" }}>
            {alias}
          </Caption1>
        )}
      </div>
    </div>
  );
};

export default PanelUserCard;
