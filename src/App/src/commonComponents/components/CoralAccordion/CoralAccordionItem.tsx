import React, { useState, isValidElement } from "react";
import { CoralAccordionContext } from "./CoralAccordionContext";

type CoralAccordionItemProps = {
  defaultOpen?: boolean;
  children: React.ReactNode;
};

const CoralAccordionItem: React.FC<CoralAccordionItemProps> = ({
  defaultOpen = false,
  children,
}) => {
  const [open, setOpen] = useState(defaultOpen);
  const toggle = () => setOpen((prev) => !prev);

  return (
    <CoralAccordionContext.Provider value={{ open, toggle }}>
      {React.Children.map(children, (child) => {
        if (!isValidElement(child)) return child;

        const type =
          (child.type as any)?.displayName || (child.type as any)?.name || "";

        // Show CoralAccordionPanel only if open
        if (type === "CoralAccordionPanel") {
          return open ? child : null;
        }

        // Render all other children (e.g., CoralAccordionHeader)
        return child;
      })}
    </CoralAccordionContext.Provider>
  );
};

export default CoralAccordionItem;
