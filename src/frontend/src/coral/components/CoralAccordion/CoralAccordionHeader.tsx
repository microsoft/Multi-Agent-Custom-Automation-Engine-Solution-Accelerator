import React from "react";
import { Body1 } from "@fluentui/react-components";
import { ChevronUp20Regular } from "@fluentui/react-icons";
import { useCoralAccordion } from "./CoralAccordionContext";

type Props = {
  children: React.ReactNode;
  height?: string;
  chevron?: boolean;
};

const CoralAccordionHeader: React.FC<Props> = ({
  children,
  chevron = false,
}) => {
  const { open, toggle } = useCoralAccordion();

  return (
    <div
      onClick={toggle}
      style={{
        color: "var(--colorNeutralForeground3)",
        padding: "0px 16px 0px 16px",
        backgroundColor: "transparent",
        cursor: "pointer",
        justifyContent: "space-between",
        display: "flex",
        alignItems: "center",
        height: '40px',
      }}
    >
      <Body1>{children}</Body1>
      {chevron && (
        <span
          style={{
            display: "flex",
            transition: "transform 0.25s ease",
            transform: open ? "rotate(-180deg)" : "rotate(0deg)",
          }}
        >
          <ChevronUp20Regular />
        </span>
      )}
    </div>
  );
};

CoralAccordionHeader.displayName = "CoralAccordionHeader";
export default CoralAccordionHeader;
