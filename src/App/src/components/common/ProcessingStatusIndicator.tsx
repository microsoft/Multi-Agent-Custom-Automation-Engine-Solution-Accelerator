import { Spinner } from '@fluentui/react-components';
import { formatElapsedTime } from '@/utils';

interface ProcessingStatusIndicatorProps {
    message: string;
    elapsedSeconds?: number;
}

const ProcessingStatusIndicator = ({
    message,
    elapsedSeconds,
}: ProcessingStatusIndicatorProps) => {
    const showElapsedSuffix = typeof elapsedSeconds === 'number' && elapsedSeconds > 0;
    const elapsedSuffix = showElapsedSuffix ? ` (${formatElapsedTime(elapsedSeconds)})` : '';

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
