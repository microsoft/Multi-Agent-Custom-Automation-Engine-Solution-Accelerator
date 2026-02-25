import { useEffect, useState } from "react";

/**
 * Hook that rotates through a list of loading messages on a timed interval.
 *
 * @param messages      - array of strings to cycle through
 * @param active        - whether the rotation should be active
 * @param intervalMs    - time in ms between rotations (default: 3000)
 * @returns the current loading message string
 */
export function useLoadingMessages(
    messages: string[],
    active: boolean,
    intervalMs = 3000
): string {
    const [message, setMessage] = useState<string>(messages[0] ?? "");

    useEffect(() => {
        if (!active || messages.length === 0) return;

        let index = 0;
        setMessage(messages[0]);

        const interval = setInterval(() => {
            index = (index + 1) % messages.length;
            setMessage(messages[index]);
        }, intervalMs);

        return () => clearInterval(interval);
    }, [active, messages, intervalMs]);

    return message;
}

export default useLoadingMessages;
