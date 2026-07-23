/**
 * useAutoScroll — smooth-scrolls a container to the bottom.
 * Extracted from PlanPage to be reusable.
 */
import { useCallback, useRef } from 'react';

export function useAutoScroll() {
    const messagesContainerRef = useRef<HTMLDivElement>(null);
    const finalResultRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = useCallback(() => {
        setTimeout(() => {
            messagesContainerRef.current?.scrollTo({
                top: messagesContainerRef.current.scrollHeight,
                behavior: 'smooth',
            });
        }, 100);
    }, []);

    // Scroll to the final result message instead of the absolute bottom.
    // Falls back to scrollToBottom when the anchor is not yet mounted.
    const scrollToFinalResult = useCallback(() => {
        setTimeout(() => {
            if (finalResultRef.current) {
                finalResultRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                scrollToBottom();
            }
        }, 150);
    }, [scrollToBottom]);

    return { messagesContainerRef, finalResultRef, scrollToBottom, scrollToFinalResult };
}

export default useAutoScroll;
