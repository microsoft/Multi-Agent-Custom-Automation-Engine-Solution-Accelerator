import { createContext, useContext } from "react";

export const CoralAccordionContext = createContext<{
  open: boolean;
  toggle: () => void;
} | null>(null);

export const useCoralAccordion = () => {
  const ctx = useContext(CoralAccordionContext);
  if (!ctx) throw new Error("Must be used inside CoralAccordionItem");
  return ctx;
};
