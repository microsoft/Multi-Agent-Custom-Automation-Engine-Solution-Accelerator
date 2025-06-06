
declare global {
    interface Window {
        activeUserId?: string;
    }
}

let USER_ID: string | undefined;

/**
 * Get the current user ID from the window.activeUserId or return a default UUID
 * @returns The user ID string
 */
export function getUserId(): string {
    USER_ID = window.activeUserId;
    const userId = USER_ID ?? "00000000-0000-0000-0000-000000000000";
    return userId;
}

/**
 * Build headers with authentication information
 * @param headers Optional additional headers to merge
 * @returns Combined headers object with authentication
 */
export function headerBuilder(headers?: Record<string, string>): Record<string, string> {
    let userId = getUserId();
    let defaultHeaders = {
        "x-ms-client-principal-id": String(userId) || "",  // Custom header
    };
    return {
        ...defaultHeaders,
        ...(headers ? headers : {})
    };
}
