import { useEffect, useCallback, RefObject } from "react";

/**
 * Hook that auto-resizes a textarea's height to fit its content.
 *
 * @param textareaRef - ref to the textarea element
 * @param value       - the current value of the textarea (triggers resize on change)
 */
export function useTextareaAutoResize(
    textareaRef: RefObject<HTMLTextAreaElement | null>,
    value: string
): {
    /** Reset the textarea height to its default ("auto") and optionally focus */
    resetHeight: (focus?: boolean) => void;
} {
    // Resize whenever value changes
    useEffect(() => {
        const el = textareaRef.current;
        if (el) {
            el.style.height = "auto";
            el.style.height = `${el.scrollHeight}px`;
        }
    }, [value, textareaRef]);

    const resetHeight = useCallback(
        (focus = false) => {
            const el = textareaRef.current;
            if (el) {
                el.style.height = "auto";
                if (focus) el.focus();
            }
        },
        [textareaRef]
    );

    return { resetHeight };
}

export default useTextareaAutoResize;
