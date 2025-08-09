import React, { useState } from "react";
import { Button, Input, makeStyles } from "@fluentui/react-components";
import { apiService } from "@/api/apiService";
import { TaskService } from "@/services/TaskService";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    height: "100%",
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  },
  messageUser: {
    alignSelf: "flex-end",
  },
  messageAssistant: {
    alignSelf: "flex-start",
  },
  inputRow: {
    display: "flex",
    gap: "4px",
  },
});

const Chat: React.FC = () => {
  const styles = useStyles();
  const [sessionId, setSessionId] = useState<string>(
    TaskService.generateSessionId()
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;

    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const response = await apiService.sendChatMessage(sessionId, text);
      if (response.session_id && response.session_id !== sessionId) {
        setSessionId(response.session_id);
      }
      const reply = (response as any).reply || (response as any).message || "";
      const assistantMessage: Message = { role: "assistant", content: reply };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Failed to send chat message", err);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.messages}>
        {messages.map((m, i) => (
          <div
            key={i}
            className={m.role === "user" ? styles.messageUser : styles.messageAssistant}
          >
            {m.content}
          </div>
        ))}
      </div>
      <div className={styles.inputRow}>
        <Input
          value={input}
          onChange={(_, data) => setInput(data.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSend();
            }
          }}
        />
        <Button onClick={handleSend}>Send</Button>
      </div>
    </div>
  );
};

export default Chat;

