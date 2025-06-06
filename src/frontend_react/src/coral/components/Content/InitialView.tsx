import {
  Body1,
  Card,
  Text,
  Title2,
  Button,
  tokens,
  Subtitle2,
  Body1Strong,
} from "@fluentui/react-components";
import {
  Send20Regular,
  Person20Regular,
  Phone20Regular,
  ShoppingBag20Regular,
  DocumentEdit20Regular,
} from "@fluentui/react-icons";
import React, { useRef, useEffect, useState } from "react";
import "./Chat.css";
import ChatInput from "../../modules/ChatInput";
import { Send } from "../../imports/bundleicons";

interface QuickTask {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

const quickTasks: QuickTask[] = [
  {
    id: "onboard",
    title: "Onboard employee",
    description: "Onboard a new employee, Jessica",
    icon: <Person20Regular />,
  },
  {
    id: "mobile",
    title: "Mobile plan query",
    description: "Ask about roaming plans prior to heading overseas",
    icon: <Phone20Regular />,
  },
  {
    id: "addon",
    title: "Buy add-on",
    description: "Enable roaming on mobile plan, starting next week",
    icon: <ShoppingBag20Regular />,
  },
  {
    id: "press",
    title: "Draft a press release",
    description: "Write a press release about our current products",
    icon: <DocumentEdit20Regular />,
  },
];

interface InitialViewProps {
  onInputSubmit: (input: string) => void;
  onQuickTaskSelect: (taskId: string) => void;
}

const InitialView: React.FC<InitialViewProps> = ({
  onInputSubmit,
  onQuickTaskSelect,
}) => {
  const [inputValue, setInputValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (inputValue.trim()) {
      onInputSubmit(inputValue.trim());
      setInputValue("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [inputValue]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: "24px",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            width: "100%",
            maxWidth: "768px",
            gap: "32px",
          }}
        >
          <div style={{ textAlign: "center", marginBottom: "24px" }}>
            <Title2>How can I help?</Title2>
          </div>

          <div style={{ width: "100%", marginBottom: "32px" }}>



            <ChatInput
              value={inputValue}
              onChange={setInputValue}
              onEnter={handleSubmit}
              placeholder="Tell us what needs planning, building, or connecting—we’ll handle the rest."
            >
              <Button
                className="send-button"
                onClick={handleSubmit}
                icon={<Send />}
                appearance="transparent"
              />
            </ChatInput>




          </div>

          <div style={{ width: "100%", marginTop: "8px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "12px",
              }}
            >
              <Body1Strong>Quick tasks</Body1Strong>
              <Button size="small"
                appearance="transparent"
              >
                Refresh
              </Button>
            </div>

            <div
              style={{
                display: "flex",
                gap: "12px",
                flexWrap: "wrap",
                justifyContent: "space-between",
              }}
            >
              {quickTasks.map((task) => (
                <Card
                  key={task.id}
                  style={{
                    flex: "1 ",
                    display: "flex",
                    flexDirection: "column",
                    padding: "16px",
                    backgroundColor: tokens.colorNeutralBackground3,
                    border: `1px solid ${tokens.colorNeutralStroke2}`,
                    borderRadius: "8px",
                    cursor: "pointer",
                    boxShadow: "none",
                  }}
                  onClick={() => onQuickTaskSelect(task.id)}
                  onMouseOver={(e) =>
                  (e.currentTarget.style.backgroundColor =
                    tokens.colorNeutralBackground4Hover)
                  }
                  onMouseOut={(e) =>
                  (e.currentTarget.style.backgroundColor =
                    tokens.colorNeutralBackground3)
                  }
                >
                  <div style={{ display: "flex", flexDirection:'column', gap: "12px" }}>
                    <div
                      style={{
                        fontSize: "20px",
                        color: tokens.colorBrandForeground1,
                        marginTop: "2px",
                      }}
                    >
                      {task.icon}
                    </div>
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "4px",
                      }}
                    >
                      <Body1Strong>{task.title}</Body1Strong>
                      <Body1 style={{ color: 'var(--colorNeutralForeground3' }}>{task.description}</Body1>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InitialView;
