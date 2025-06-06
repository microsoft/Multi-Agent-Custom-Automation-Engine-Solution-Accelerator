import {
    Body1,
    Button,
    Card,
    Checkbox,
    Divider,
    Persona,
    Text,
    Subtitle1,
} from "@fluentui/react-components";
import { Add20Regular } from "@fluentui/react-icons";
import React from "react";
import { TaskDetailsProps } from "../../models";
import "../../styles/TaskDetails.css";

const TaskDetails: React.FC<TaskDetailsProps> = ({
    taskName,
    subTasks,
    agents,
    humans,

}) => {
    const completedCount = subTasks.filter(t => t.status === 'completed').length;

    return (
        <div className="task-details-container">
            <div className="task-details-section">
                <div className="task-details-progress-header">
                    <Subtitle1>{taskName}</Subtitle1>
                    <Text size={200}>
                        {completedCount} of {subTasks.length} completed
                    </Text>
                </div>
                <div className="task-details-subtask-list">
                    {subTasks.map((subtask) => (
                        <Checkbox
                            key={subtask.id}
                            checked={subtask.status === 'completed'}
                            disabled
                            label={subtask.name}
                        />
                    ))}
                </div>
            </div>

            <Divider />

            <div className="task-details-section">
                <Subtitle1>Agents</Subtitle1>
                {agents.map((agent) => (
                    <Card key={agent.id} className="task-details-agent-card">
                        <Persona
                            name={agent.name}
                            secondaryText={agent.description}
                            avatar={{ image: { src: agent.avatarUrl } }}
                            presence={{ status: "available" }}
                        />
                    </Card>
                ))}

            </div>

            <Divider />

            <div className="task-details-section">
                <Subtitle1>Humans</Subtitle1>
                {humans.map((human) => (
                    <Card key={human.id} className="task-details-agent-card">
                        <Persona
                            name={human.name}
                            secondaryText={human.email}
                            avatar={{ image: { src: human.avatarUrl } }}
                            presence={{ status: "available" }}
                        />
                    </Card>
                ))}
            </div>
        </div>
    );
};

export default TaskDetails; 