import React, { useEffect, useState } from 'react';
import { FluentProvider, webLightTheme, Button, Spinner, Text, Card, CardHeader, Input, makeStyles, tokens } from '@fluentui/react-components';
import { useGetPlans, useSubmitInputTask, useSubmitClarification } from '../hooks';
import { apiService } from '../api/apiService';
import { PlanWithSteps, StepStatus, InputTask } from '../models';

const useStyles = makeStyles({
    container: {
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        padding: '20px',
        maxWidth: '800px',
        margin: '0 auto',
    },
    card: {
        marginBottom: '16px',
    },
    header: {
        fontWeight: 'bold',
    },
    form: {
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        marginBottom: '20px',
    },
    inputRow: {
        display: 'flex',
        gap: '8px',
    },
    planGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: '16px',
    },
    planCard: {
        height: '100%',
    },
    stepsList: {
        padding: '0 0 0 20px',
    },
    statusBadge: {
        padding: '4px 8px',
        borderRadius: '4px',
        fontSize: '12px',
        fontWeight: 'bold',
    },
    planned: {
        backgroundColor: tokens.colorNeutralBackground3,
    },
    awaiting: {
        backgroundColor: tokens.colorBrandBackground,
        color: tokens.colorNeutralForegroundOnBrand,
    },
    approved: {
        backgroundColor: tokens.colorSuccessBackground2,
    },
    rejected: {
        backgroundColor: tokens.colorDangerBackground2,
    },
    completed: {
        backgroundColor: tokens.colorSuccessBackground,
        color: tokens.colorNeutralForegroundOnBrand,
    },
    failed: {
        backgroundColor: tokens.colorDangerBackground,
        color: tokens.colorNeutralForegroundOnBrand,
    },
    buttonRow: {
        display: 'flex',
        gap: '8px',
    },
    progress: {
        marginTop: '8px',
        height: '8px',
        backgroundColor: tokens.colorNeutralBackground3,
        borderRadius: '4px',
        overflow: 'hidden',
    },
    progressBar: {
        height: '100%',
        backgroundColor: tokens.colorBrandBackground,
        transition: 'width 0.3s ease',
    },
});

const ApiServiceExample: React.FC = () => {
    const styles = useStyles();
    const [taskDescription, setTaskDescription] = useState('');
    const [clarification, setClarification] = useState('');
    const [activePlanId, setActivePlanId] = useState<string>('');
    const [sessionId, setSessionId] = useState<string>('');

    // Use our custom hooks
    const {
        data: plans,
        loading: plansLoading,
        error: plansError,
        execute: fetchPlans,
    } = useGetPlans();

    const {
        loading: submitLoading,
        error: submitError,
        execute: submitTask,
    } = useSubmitInputTask();

    const {
        loading: clarificationLoading,
        error: clarificationError,
        execute: submitClarificationFn,
    } = useSubmitClarification();

    // Fetch plans on component mount
    useEffect(() => {
        fetchPlans();
        // Refresh plans every 10 seconds
        const interval = setInterval(() => {
            fetchPlans();
        }, 10000);

        return () => clearInterval(interval);
    }, [fetchPlans]);

    const handleSubmitTask = async () => {
        if (!taskDescription.trim()) return;

        const inputTask: InputTask = {
            description: taskDescription,
            session_id: sessionId || undefined
        };

        const response = await submitTask(inputTask);
        if (response) {
            setSessionId(response.session_id);
            setActivePlanId(response.plan_id);
            setTaskDescription('');
            // Refresh plans after submission
            fetchPlans();
        }
    };

    const handleClarify = async () => {
        if (!clarification.trim() || !activePlanId || !sessionId) return;

        await submitClarificationFn(activePlanId, sessionId, clarification);
        setClarification('');
        // Refresh plans after clarification
        fetchPlans();
    };

    const getStatusClass = (status: StepStatus) => {
        switch (status) {
            case StepStatus.PLANNED:
                return styles.planned;
            case StepStatus.AWAITING_FEEDBACK:
                return styles.awaiting;
            case StepStatus.APPROVED:
                return styles.approved;
            case StepStatus.REJECTED:
                return styles.rejected;
            case StepStatus.COMPLETED:
                return styles.completed;
            case StepStatus.FAILED:
                return styles.failed;
            default:
                return '';
        }
    };

    return (
        <FluentProvider theme={webLightTheme}>
            <div className={styles.container}>
                <Text size={700} weight="bold">Unified API Service Demo</Text>

                <Card className={styles.card}>
                    <CardHeader header={<Text weight="bold">Create New Task</Text>} />
                    <div className={styles.form}>
                        <Input
                            value={taskDescription}
                            onChange={(e, data) => setTaskDescription(data.value)}
                            placeholder="Enter task description..."
                        />
                        <div className={styles.inputRow}>
                            <Input
                                value={sessionId}
                                onChange={(e, data) => setSessionId(data.value)}
                                placeholder="Session ID (optional)"
                            />
                            <Button
                                appearance="primary"
                                onClick={handleSubmitTask}
                                disabled={!taskDescription.trim() || submitLoading}
                            >
                                {submitLoading ? <Spinner size="tiny" /> : 'Create Task'}
                            </Button>
                        </div>
                        {submitError && <Text color="red">{submitError.message}</Text>}
                    </div>
                </Card>

                {activePlanId && sessionId && (
                    <Card className={styles.card}>
                        <CardHeader header={<Text weight="bold">Add Clarification</Text>} />
                        <div className={styles.form}>
                            <Input
                                value={clarification}
                                onChange={(e, data) => setClarification(data.value)}
                                placeholder="Enter clarification..."
                            />
                            <Button
                                onClick={handleClarify}
                                disabled={!clarification.trim() || clarificationLoading}
                            >
                                {clarificationLoading ? <Spinner size="tiny" /> : 'Submit Clarification'}
                            </Button>
                            {clarificationError && <Text color="red">{clarificationError.message}</Text>}
                        </div>
                    </Card>
                )}

                <div className={styles.buttonRow}>
                    <Button onClick={() => fetchPlans()} disabled={plansLoading}>
                        {plansLoading ? <Spinner size="tiny" /> : 'Refresh Plans'}
                    </Button>
                    <Button onClick={() => apiService.clearCache()}>
                        Clear Cache
                    </Button>
                </div>

                {plansError && <Text color="red">{plansError.message}</Text>}

                {plansLoading && !plans && <Spinner />}

                <div className={styles.planGrid}>
                    {plans?.map((plan: PlanWithSteps) => {
                        const completionPercentage = apiService.getPlanCompletionPercentage(plan);

                        return (
                            <Card key={plan.id} className={styles.planCard}>
                                <CardHeader
                                    header={<Text weight="bold">{plan.initial_goal}</Text>}
                                    description={`ID: ${plan.id} | Session: ${plan.session_id}`}
                                />
                                <div className={styles.progress}>
                                    <div
                                        className={styles.progressBar}
                                        style={{ width: `${completionPercentage}%` }}
                                    />
                                </div>
                                <Text>{completionPercentage}% Complete</Text>

                                <Text weight="semibold" block>Steps:</Text>
                                <ul className={styles.stepsList}>
                                    {plan.steps.map((step) => (
                                        <li key={step.id}>
                                            <Text>{step.action}</Text>
                                            <div>
                                                <span className={`${styles.statusBadge} ${getStatusClass(step.status)}`}>
                                                    {step.status}
                                                </span>
                                            </div>
                                        </li>
                                    ))}
                                </ul>

                                <Button
                                    onClick={() => {
                                        setActivePlanId(plan.id);
                                        setSessionId(plan.session_id);
                                    }}
                                >
                                    Select Plan
                                </Button>
                            </Card>
                        );
                    })}
                </div>
            </div>
        </FluentProvider>
    );
};

export default ApiServiceExample;
