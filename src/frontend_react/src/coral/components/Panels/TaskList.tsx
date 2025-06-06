import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
  Button,
  Menu,
  MenuList,
  MenuItem,
  MenuPopover,
  MenuTrigger,
  Caption1,
  Body1,
} from "@fluentui/react-components";
import { MoreHorizontal20Regular } from "@fluentui/react-icons";
import React, { useState, useRef, useEffect } from "react";
import "../../apptest.css";

export interface Task {
  id: string;
  name: string;
  status: "inprogress" | "completed";
  date?: string;
}

interface TaskListProps {
  inProgressTasks: Task[];
  completedTasks: Task[];
  onTaskSelect: (taskId: string) => void;
  onTaskRename: (taskId: string, newName: string) => void;
  onTaskDelete: (taskId: string) => void;
  activeTaskId: string | null;
}

const TaskList: React.FC<TaskListProps> = ({
  inProgressTasks,
  completedTasks,
  onTaskSelect,
  onTaskRename,
  onTaskDelete,
  activeTaskId,
}) => {
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (editingTaskId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingTaskId]);

  const beginRename = (taskId: string, currentName: string) => {
    setEditingTaskId(taskId);
    setEditValue(currentName);
  };

  const submitRename = (taskId: string) => {
    const trimmed = editValue.trim();
    if (trimmed.length > 0) {
      onTaskRename(taskId, trimmed);
    }
    setEditingTaskId(null);
  };

  const cancelRename = () => {
    setEditingTaskId(null);
    setEditValue("");
  };

  const renderTaskItem = (task: Task) => {
    const isActive = activeTaskId === task.id;
    const isEditing = editingTaskId === task.id;

    return (
      <div
        key={task.id}
        className={`task-tab ${isActive ? "active" : ""}`}
        onClick={() => onTaskSelect(task.id)}
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
        }}
      >
        <div className="sideNavTick" />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flex: 1,
          }}
        >
          <div className="left">
            {isEditing ? (
              <input
                ref={inputRef}
                value={editValue}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submitRename(task.id);
                  else if (e.key === "Escape") cancelRename();
                }}
                onBlur={() => submitRename(task.id)}
                style={{
                  fontSize: "14px",
                  padding: 0,
                  margin: 0,
                  border: "none",
                  outline: "none",
                  background: "transparent",
                  color: "var(--colorNeutralForeground1)",
                  fontWeight: 500,
                  width: "100%",
                }}
              />
            ) : (
              <div>{task.name}</div>
            )}
            {task.date && (
              <Caption1
                style={{
                  color: "var(--colorNeutralForeground3)",
                  marginTop: "2px",
                }}
              >
                {task.date}
              </Caption1>
            )}
          </div>
<Menu>
  <MenuTrigger>
    <Button
      appearance="transparent"
      icon={<MoreHorizontal20Regular />}
      onClick={(e) => e.stopPropagation()}
      className="task-menu-button"
    />
  </MenuTrigger>
  <MenuPopover>
    <MenuList>
      <MenuItem
        onClick={(e) => {
          e.stopPropagation();
          beginRename(task.id, task.name);
        }}
      >
        Rename
      </MenuItem>
      <MenuItem
        onClick={(e) => {
          e.stopPropagation();
          onTaskDelete(task.id);
        }}
      >
        Delete
      </MenuItem>
    </MenuList>
  </MenuPopover>
</Menu>

        </div>
      </div>
    );
  };

  return (
    <Accordion defaultOpenItems={["inprogress"]} collapsible>
      <AccordionItem value="inprogress">
        <AccordionHeader
          expandIconPosition="end"
          style={{
            color: "var(--colorNeutralForeground3)",
            padding: "0px 16px 0px 0",
            backgroundColor: "transparent",
            cursor: "pointer",
            justifyContent: "space-between",
            height: "32px",
          }}
        >
          <Body1>In progress</Body1>
        </AccordionHeader>

        <AccordionPanel style={{ margin: "8px" }}>
          {inProgressTasks.map(renderTaskItem)}
        </AccordionPanel>
      </AccordionItem>
      <AccordionItem value="completed">
        <AccordionHeader
          expandIconPosition="end"
          style={{
            color: "var(--colorNeutralForeground3)",
            padding: "0px 16px 0px 0",
            backgroundColor: "transparent",
            cursor: "pointer",
            justifyContent: "space-between",
            height: "32px",
          }}
        >
          <Body1>Completed</Body1>
        </AccordionHeader>

        <AccordionPanel>{completedTasks.map(renderTaskItem)}</AccordionPanel>
      </AccordionItem>
    </Accordion>
  );
};

export default TaskList;
