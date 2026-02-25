import {
  Button,
  Menu,
  MenuTrigger,
  Caption1,
  Skeleton,
  SkeletonItem,
} from "@fluentui/react-components";
import { MoreHorizontal20Regular } from "@fluentui/react-icons";
import React, { useCallback } from "react";
import "../../styles/TaskList.css";
import { Task, TaskListProps } from "@/models";
import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
} from "@fluentui/react-components";

const TaskList: React.FC<TaskListProps> = React.memo(({
  completedTasks,
  onTaskSelect,
  loading,
  selectedTaskId,
  isLoadingTeam
}) => {
  const renderTaskItem = useCallback((task: Task) => {
    const isActive = task.id === selectedTaskId;

    return (
      <div
        key={task.id}
        className={`task-tab${isActive ? " active" : ""}`}
        role="button"
        tabIndex={0}
        onClick={() => onTaskSelect(task.id)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onTaskSelect(task.id);
          }
        }}
      >
        <div className="sideNavTick" />
        <div className="left">
          <div className="task-name-truncated" title={task.name}>
            {task.name}
          </div>
          {task.date && task.status == "completed" && (
            <Caption1 className="task-list-task-date">{task.date}</Caption1>
          )}
          {/* {task.status == "inprogress" && (
            <Caption1 className="task-list-task-date">{`${task?.completed_steps} of ${task?.total_steps} completed`}</Caption1>
          )} */}
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
  }, [selectedTaskId, onTaskSelect]);

  const renderSkeleton = (key: string) => (
    <div key={key} className="task-skeleton-container">
      <Skeleton aria-label="Loading task">
        <div className="task-skeleton-wrapper">
          <SkeletonItem shape="rectangle" animation="wave" size={24} />
        </div>
      </Skeleton>
    </div>
  );

  return (
    <div className="task-list-container">
      <Accordion defaultOpenItems="1" collapsible>
        <AccordionItem value="1">
          <AccordionHeader expandIconPosition="end">
            Completed
          </AccordionHeader>
          <AccordionPanel>
            {(loading || isLoadingTeam)
              ? Array.from({ length: 5 }, (_, i) =>
                renderSkeleton(`completed-${i}`)
              )
              : completedTasks.map(renderTaskItem)}
          </AccordionPanel>
        </AccordionItem>

      </Accordion>
    </div>
  );
});
TaskList.displayName = 'TaskList';

export default TaskList;
