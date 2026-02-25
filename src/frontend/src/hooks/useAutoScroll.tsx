import { useCallback, useEffect, useRef } from "react";

export interface UseAutoScrollOptions {
    /** Delay in ms before scrolling (default: 100) */
    delay?: number;
    /** Scroll behavior (default: "smooth") */
    behavior?: ScrollBehavior;
}

export interface UseAutoScrollReturn {
    /** Ref to attach to the scrollable container */
    containerRef: React.RefObject<HTMLDivElement | null>;
    /** Manually trigger a scroll-to-bottom */
    scrollToBottom: () => void;
}

/**
 * Hook that provides auto-scroll-to-bottom behaviour for a container.
 *
 * Attach `containerRef` to the scrollable element. Call `scrollToBottom()`
 * or pass `dependencies` that, when they change, will automatically scroll.
 *
 * @param dependencies - values whose changes trigger an automatic scroll
 * @param options      - delay & scroll behaviour overrides
 */
export function useAutoScroll(
    dependencies: React.DependencyList = [],
    options: UseAutoScrollOptions = {}
): UseAutoScrollReturn {
    const { delay = 100, behavior = "smooth" } = options;
    const containerRef = useRef<HTMLDivElement | null>(null);

    const scrollToBottom = useCallback(() => {
        setTimeout(() => {
            if (containerRef.current) {
                containerRef.current.scrollTo({
                    top: containerRef.current.scrollHeight,
                    behavior,
                });
            }
        }, delay);
    }, [delay, behavior]);

    // Auto-scroll whenever any dependency changes
    useEffect(() => {
        scrollToBottom();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, dependencies);

    return { containerRef, scrollToBottom };
}

export default useAutoScroll;
