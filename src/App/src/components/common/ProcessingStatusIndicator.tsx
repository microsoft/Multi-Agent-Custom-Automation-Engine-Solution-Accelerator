import { Spinner } from '@fluentui/react-components';

interface ProcessingStatusIndicatorProps {
    message: string;
    elapsedSeconds?: number;
}

const formatElapsedTime = (elapsedSeconds: number): string => {
    if (elapsedSeconds < 60) {
        return `${elapsedSeconds}s`;
    }

    const minutes = Math.floor(elapsedSeconds / 60);
    const seconds = elapsedSeconds % 60;
    return `${minutes}min ${seconds}sec`;
};

const ProcessingStatusIndicator = ({
    message,
    elapsedSeconds,
}: ProcessingStatusIndicatorProps) => {
    const showElapsedSuffix = Number.isFinite(elapsedSeconds) && (elapsedSeconds as number) > 0;
    const elapsedSuffix = showElapsedSuffix ? ` (${formatElapsedTime(elapsedSeconds as number)})` : '';

    return (
        <div
            style={{
                maxWidth: '800px',
                margin: '0 auto 32px auto',
                padding: '0 24px',
            }}
        >
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    backgroundColor: 'var(--colorNeutralBackground2)',
                    borderRadius: '8px',
                    border: '1px solid var(--colorNeutralStroke1)',
                    padding: '16px',
                }}
            >
                <Spinner size="small" />
                <span
                    style={{
                        fontSize: '14px',
                        color: 'var(--colorNeutralForeground1)',
                        fontWeight: '500',
                    }}
                >
                    {message}
                    {elapsedSuffix}
                </span>
            </div>
        </div>
    );
};

export default ProcessingStatusIndicator;
