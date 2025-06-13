import React, { useEffect, useState } from "react";
import {
  CheckmarkCircle20Regular,
  Info20Regular,
  Warning20Regular,
  DismissCircle20Regular,
  Dismiss20Regular,
} from "@fluentui/react-icons";
import { Body1, Spinner } from "@fluentui/react-components";

// Toast type
export type ToastIntent = "info" | "success" | "warning" | "error" | "progress";

// Toast data structure
type Toast = {
  id: number;
  content: React.ReactNode;
  intent: ToastIntent;
  visible: boolean;
  dismissible?: boolean;
};

// Internal state setter reference
let _setToasts: React.Dispatch<React.SetStateAction<Toast[]>> | null = null;

// Hook for triggering toasts
export const useInlineToaster = () => {
  const showToast = (
    content: React.ReactNode,
    intent: ToastIntent = "info",
    options?: { dismissible?: boolean }
  ) => {
    const id = Date.now();
    if (_setToasts) {
      _setToasts((prev) => [
        ...prev,
        { id, content, intent, visible: false, dismissible: options?.dismissible },
      ]);

      setTimeout(() => {
        _setToasts?.((prev) =>
          prev.map((t) => (t.id === id ? { ...t, visible: true } : t))
        );
      }, 10);

      if (intent !== "progress") {
        setTimeout(() => {
          _setToasts?.((prev) =>
            prev.map((t) => (t.id === id ? { ...t, visible: false } : t))
          );
        }, 3000);

        setTimeout(() => {
          _setToasts?.((prev) => prev.filter((t) => t.id !== id));
        }, 3500);
      }
    }
    return id;
  };

  const dismissToast = (id: number) => {
    _setToasts?.((prev) =>
      prev.map((t) => (t.id === id ? { ...t, visible: false } : t))
    );
    setTimeout(() => {
      _setToasts?.((prev) => prev.filter((t) => t.id !== id));
    }, 500);
  };

  return { showToast, dismissToast };
};

// Icon mapping
const getIconForIntent = (intent: ToastIntent) => {
  switch (intent) {
    case "success":
      return <CheckmarkCircle20Regular />;
    case "info":
      return <Info20Regular />;
    case "warning":
      return <Warning20Regular />;
    case "error":
      return <DismissCircle20Regular />;
    case "progress":
      return <Spinner size="tiny" />;
    default:
      return null;
  }
};

// Toaster render mount
const InlineToaster: React.FC = () => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    _setToasts = setToasts;
    return () => {
      _setToasts = null;
    };
  }, []);

  return (
    <div
      style={{
        position: "absolute",
        bottom: 24,
        left: "50%",
        transform: "translateX(-50%)",
        display: "flex",
        flexDirection: "column-reverse",
        gap: 8,
        zIndex: 1000,
        pointerEvents: "none",
      }}
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          style={{
            background: "var(--colorNeutralBackground3)",
            border: "1px solid var(--colorNeutralStroke1)",
            padding: "16px",
            borderRadius: 9999,
            color: "var(--colorNeutralForeground1)",
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
            minWidth: 160,
            textAlign: "left",
            fontSize: 14,
            display: "flex",
            alignItems: "center",
            gap: 8,
            opacity: toast.visible ? 1 : 0,
            transform: toast.visible ? "translateY(0px)" : "translateY(20px)",
            transition: "opacity 0.3s ease, transform 0.3s ease",
            pointerEvents: "auto",
            position: "relative",
          }}
        >
          <span style={{ display: "flex", alignItems: "center" }}>
            {getIconForIntent(toast.intent)}
          </span>
          <Body1>{toast.content}</Body1>
          {toast.dismissible && (
            <button
              onClick={() => _setToasts?.((prev) => prev.filter((t) => t.id !== toast.id))}
              style={{
                position: "absolute",
                top: "50%",
                right: 8,
                transform: "translateY(-50%)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                color: "var(--colorNeutralForeground1)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              aria-label="Dismiss"
            >
              <Dismiss20Regular />
            </button>
          )}
        </div>
      ))}
    </div>
  );
};

export default InlineToaster;
