import React, { useEffect, useState } from "react";
import {
  CheckmarkCircle20Regular,
  Info20Regular,
  Warning20Regular,
  DismissCircle20Regular,
  Dismiss20Regular,
} from "@fluentui/react-icons";
import { Body1, Button, Spinner, Tooltip } from "@fluentui/react-components";

// Toast type
export type ToastIntent = "info" | "success" | "warning" | "error" | "progress";

type Toast = {
  id: number;
  content: React.ReactNode;
  intent: ToastIntent;
  visible: boolean;
  dismissible?: boolean;
};

let _setToasts: React.Dispatch<React.SetStateAction<Toast[]>> | null = null;

export const useInlineToaster = () => {
  const showToast = (
    content: React.ReactNode,
    intent: ToastIntent = "info",
    options?: {
      dismissible?: boolean;
      timeoutMs?: number | null;
    }
  ) => {
    const id = Date.now();
    const timeout = options?.timeoutMs ?? (intent === "progress" ? null : 3000);

    if (_setToasts) {
      _setToasts((prev) => [
        ...prev,
        {
          id,
          content,
          intent,
          visible: false,
          dismissible: options?.dismissible,
        },
      ]);

      setTimeout(() => {
        _setToasts?.((prev) =>
          prev.map((t) => (t.id === id ? { ...t, visible: true } : t))
        );
      }, 10);

      if (timeout !== null) {
        setTimeout(() => {
          _setToasts?.((prev) =>
            prev.map((t) => (t.id === id ? { ...t, visible: false } : t))
          );
        }, timeout);

        setTimeout(() => {
          _setToasts?.((prev) => prev.filter((t) => t.id !== id));
        }, timeout + 500);
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
                alignContent:'center'
      }}
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          style={{
            background: "var(--colorNeutralBackground3)",
            border: "1px solid var(--colorNeutralStroke1)",
            padding: "12px 16px",
            borderRadius: 9999,
            color: "var(--colorNeutralForeground1)",
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
            display: "flex",
            alignItems: "center",
            fontSize: 14,
            gap: 8,
            opacity: toast.visible ? 1 : 0,
            transform: toast.visible ? "translateY(0px)" : "translateY(20px)",
            transition: "opacity 0.3s ease, transform 0.3s ease",
            pointerEvents: "auto",
            maxWidth: "calc(100vw - 48px)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            justifyContent:'center',
        alignContent:'center',
        height:'54px',
        boxSizing:'border-box'
          }}
        >
          <span style={{ flexShrink: 0 }}>{getIconForIntent(toast.intent)}</span>

          <Body1
            style={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              flexGrow: 1,
            }}
          >
            {toast.content}
          </Body1>

          {(toast.dismissible || toast.intent === "progress") && (
            <Tooltip
                        content="Close"
                        relationship="label"
                        positioning="above"
                        withArrow
                      >
            <Button
              onClick={() =>
                _setToasts?.((prev) => prev.filter((t) => t.id !== toast.id))
              }
              style={{
                background: "transparent",
                border: "none",
                cursor: "pointer",
                color: "var(--colorNeutralForeground1)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
              aria-label="Dismiss"
              icon={<Dismiss20Regular />}
              appearance="subtle"
              shape="circular"
            >
              
              
            </Button>
            </Tooltip>
          )}
        </div>
      ))}
    </div>
  );
};

export default InlineToaster;
