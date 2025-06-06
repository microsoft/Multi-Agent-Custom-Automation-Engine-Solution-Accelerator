import {
  Body1Strong,
  Button,
  Card,
  Checkbox,
  Divider,
  Persona,
  Subtitle1,
  Caption1,
} from "@fluentui/react-components";
import { Add20Regular } from "@fluentui/react-icons";
import React from "react";

interface SubTask {
  id: string;
  name: string;
  status: "completed" | "working" | "removed";
}

interface Agent {
  id: string;
  name: string;
  description: string;
  avatarUrl?: string;
}

interface Human {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
}

interface TaskDetailsProps {
  taskName: string;
  subTasks: SubTask[];
  agents: Agent[];
  humans: Human[];
  onAddAgent: () => void;
  onAddHuman: () => void;
}

const TaskDetails: React.FC<TaskDetailsProps> = ({
  taskName,
  subTasks,
  agents,
  humans,
  onAddAgent,
  onAddHuman,
}) => {
  const completedCount = subTasks.filter((t) => t.status === "completed").length;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "auto",
      }}
    >
      {/* Subtasks Section */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          padding: "24px 16px",
          borderBottom: '1px solid var(--colorNeutralStroke2)'
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",

          }}
        >
          <Body1Strong>{taskName}</Body1Strong>
          <Caption1 style={{ color: "var(--colorNeutralForeground3)" }}>
            {completedCount} of {subTasks.length} completed
          </Caption1>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          {subTasks.map((subtask) => (
            <Checkbox
              key={subtask.id}
              checked={subtask.status === "completed"}
              disabled
              label={subtask.name}
            />
          ))}
        </div>
      </div>



      {/* Agents Section */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          padding: "24px 16px",
          borderBottom: '1px solid var(--colorNeutralStroke2)'
        }}
      >
        <Body1Strong>Agents</Body1Strong>
        {agents.map((agent) => (
          <Card key={agent.id} style={{ padding: "2px 0", cursor: "default", boxShadow: 'none', backgroundColor:'transparent'}}>
            <Persona
              name={agent.name}
              secondaryText={agent.description}
              avatar={{ image: { src: agent.avatarUrl } }}
              // presence={{ status: "available" }}
            />
          </Card>
        ))}
        <Button
          icon={<Add20Regular />}
          onClick={onAddAgent}
          style={{ alignSelf: "flex-start" }}
        >
          Add more
        </Button>
      </div>



      {/* Humans Section */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          padding: "24px 16px",
          borderBottom: '1px solid var(--colorNeutralStroke2)'
        }}
      >
        <Body1Strong>Humans</Body1Strong>
        {humans.map((human) => (
          <Card key={human.id} style={{ padding: "2px 0", cursor: "default", boxShadow: 'none', backgroundColor:'transparent' }}>
            <Persona
              name={human.name}
              secondaryText={human.email}
              avatar={{ image: { src: human.avatarUrl } }}
              // presence={{ status: "available" }}
            />
          </Card>
        ))}
        <Button
          icon={<Add20Regular />}
          onClick={onAddHuman}
          style={{ alignSelf: "flex-start" }}
        >
          Add more
        </Button>
      </div>
    </div>
  );
};

export default TaskDetails;
