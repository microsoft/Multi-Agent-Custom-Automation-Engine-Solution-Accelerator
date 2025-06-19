import React, {
  useState,
  useEffect,
  ReactElement,
  cloneElement,
  isValidElement
} from "react";
import {
  Toolbar,
  ToggleButton,
  ToggleButtonProps,
  Button,
  ButtonProps
} from "@fluentui/react-components";
import { PanelRightContract, PanelRightExpand } from "@/coral/imports/bundleicons";
import eventBus from "../eventbus.js";

type PanelRightTogglesProps = {
  children: React.ReactNode;
};

type PanelToggleExtras = {
  panelToggleIcon?: boolean;
};

type AnyButtonProps = (ToggleButtonProps | ButtonProps) & PanelToggleExtras;

const PanelRightToggles: React.FC<PanelRightTogglesProps> = ({ children }) => {
  const [activePanel, setActivePanel] = useState<"first" | "second" | "third" | "fourth" | null>(null);
  const panelTypes = ["first", "second", "third", "fourth"] as const;

  useEffect(() => {
    // Sync to current state
    setActivePanel(eventBus.getActivePanel());

    const handlePanelToggle = (panel: typeof panelTypes[number] | null) => {
      setActivePanel(panel);
    };

    const handlePanelInit = ({ panelType, isActive }: { panelType: string; isActive: boolean }) => {
      if (isActive) setActivePanel(panelType as any);
    };

    eventBus.on("setActivePanel", handlePanelToggle);
    eventBus.on("panelInitState", handlePanelInit);

    return () => {
      eventBus.off("setActivePanel", handlePanelToggle);
      eventBus.off("panelInitState", handlePanelInit);
    };
  }, []);

  const togglePanel = (panel: typeof panelTypes[number]) => {
    const next = activePanel === panel ? null : panel;
    eventBus.setActivePanel(next);
  };

  const isFluentButton = (child: React.ReactNode): child is ReactElement<AnyButtonProps> =>
    isValidElement(child) &&
    (child.type === ToggleButton || child.type === Button);

  return (
    <Toolbar style={{ padding: "4px 0", display: "flex", flexDirection: "row-reverse" }}>
      {React.Children.map(children, (child, index) => {
        const panelType = panelTypes[index];

        if (isFluentButton(child) && panelType) {
          const isActive = activePanel === panelType;
          const { panelToggleIcon, icon, ...rest } = child.props as AnyButtonProps;

          const resolvedIcon = panelToggleIcon
            ? isActive
              ? <PanelRightContract />
              : <PanelRightExpand />
            : icon;

          return cloneElement(child, {
            ...rest,
            icon: resolvedIcon,
            onClick: () => togglePanel(panelType),
            "aria-pressed": isActive,
            checked: "checked" in child.props ? isActive : undefined,
          });
        }

        return child;
      })}
    </Toolbar>
  );
};

export default PanelRightToggles;
