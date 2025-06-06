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
} from "@fluentui/react-components";
import { MoreHorizontal20Regular } from "@fluentui/react-icons";
import React from "react";
import "../../styles/TaskList.css";
import { TaskListProps, Task } from "../../models/taskList";



const TaskList: React.FC<TaskListProps> = ({
    inProgressTasks,
    completedTasks,
    onTaskSelect,
}) => {
    const renderTaskItem = (task: Task) => (<div
        key={task.id}
        className="task-list-task-item"
        onClick={() => onTaskSelect(task.id)}
    >
        <div>
            <div>{task.name}</div>
            {task.date && (
                <div className="task-list-task-date">
                    {task.date}
                </div>
            )}
        </div>            <Menu>
            <MenuTrigger>
                <Button
                    appearance="subtle"
                    icon={<MoreHorizontal20Regular />}
                    onClick={(e: React.MouseEvent) => e.stopPropagation()}
                />
            </MenuTrigger>
        </Menu>
    </div>
    );

    return (
        <Accordion defaultOpenItems={["inprogress"]} collapsible>
            <AccordionItem value="inprogress">
                <AccordionHeader>
                    In progress
                </AccordionHeader>
                <AccordionPanel>
                    {inProgressTasks.map(renderTaskItem)}
                </AccordionPanel>
            </AccordionItem>
            <AccordionItem value="completed">
                <AccordionHeader>
                    Completed
                </AccordionHeader>
                <AccordionPanel>
                    {completedTasks.map(renderTaskItem)}
                </AccordionPanel>
            </AccordionItem>
        </Accordion>
    );
};

export default TaskList; 