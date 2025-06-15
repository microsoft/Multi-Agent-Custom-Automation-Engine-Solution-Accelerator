import {
  Button,
  Menu,
  MenuTrigger,
  Caption1,
  Skeleton,
  SkeletonItem,
} from "@fluentui/react-components";
import { MoreHorizontal20Regular } from "@fluentui/react-icons";
import React from "react";
import "../../styles/TaskList.css";
import { Task, TaskListProps } from "@/models";
import CoralAccordion from "@/coral/components/CoralAccordion/CoralAccordion";
import CoralAccordionItem from "@/coral/components/CoralAccordion/CoralAccordionItem";
import CoralAccordionHeader from "@/coral/components/CoralAccordion/CoralAccordionHeader";
import CoralAccordionPanel from "@/coral/components/CoralAccordion/CoralAccordionPanel";





const TaskList: React.FC<TaskListProps> = ({
  inProgressTasks,
  completedTasks,
  onTaskSelect,
  loading,
  selectedTaskId,
}) => {
  const renderTaskItem = (task: Task) => {
    const isActive = task.id === selectedTaskId;

    return (
      <div
        key={task.id}
        className={`task-tab${isActive ? " active" : ""}`}
        onClick={() => onTaskSelect(task.id)}
      >
        <div className="sideNavTick" />
        <div className="left">
          <div>{task.name}</div>
          {task.date && (
            <Caption1 className="task-list-task-date">{task.date}</Caption1>
          )}
        </div>
        <Menu>
          <MenuTrigger>
            <Button
              appearance="subtle"
              icon={<MoreHorizontal20Regular />}
              onClick={(e: React.MouseEvent) => e.stopPropagation()}
              className="task-menu-button"
            />
          </MenuTrigger>
        </Menu>
      </div>
    );
  };

  const renderSkeleton = (key: string) => (
    <div key={key} className="task-skeleton-container">
      <Skeleton aria-label="Loading task">
        <div className="task-skeleton-wrapper">
          <SkeletonItem
            shape="rectangle"
            animation="wave"
            size={24}
          />
        </div>
      </Skeleton>
    </div>
  );

  return (
    <CoralAccordion>
      <CoralAccordionItem defaultOpen>
        <CoralAccordionHeader chevron>In progress</CoralAccordionHeader>

        <CoralAccordionPanel>
          {loading && inProgressTasks.length === 0
            ? [...Array(3)].map((_, i) =>
              renderSkeleton(`inprogress-skel-${i}`)
            )
            : inProgressTasks.map(renderTaskItem)}
        </CoralAccordionPanel>
      </CoralAccordionItem>

      <CoralAccordionItem>
        <CoralAccordionHeader chevron>Completed</CoralAccordionHeader>

        <CoralAccordionPanel>
          {loading && completedTasks.length === 0
            ? [...Array(2)].map((_, i) => renderSkeleton(`completed-skel-${i}`))
            : completedTasks.map(renderTaskItem)}
        </CoralAccordionPanel>
      </CoralAccordionItem>
    </CoralAccordion>
  );
};

export default TaskList;
