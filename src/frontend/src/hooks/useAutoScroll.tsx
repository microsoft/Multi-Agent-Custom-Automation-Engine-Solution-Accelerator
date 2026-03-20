/**
 * useAutoScroll — smooth-scrolls a container to the bottom.
 * Extracted from PlanPage to be reusable.
 */
import { useCallback, useRef } from 'react';

export function useAutoScroll() {
    const messagesContainerRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = useCallback(() => {
        setTimeout(() => {
            messagesContainerRef.current?.scrollTo({
                top: messagesContainerRef.current.scrollHeight,
                behavior: 'smooth',
            });
        }, 100);
    }, []);

    return { messagesContainerRef, scrollToBottom };
}

export default useAutoScroll;
