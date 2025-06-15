// src/config.js

import { UserInfo } from "@/models";

declare global {
    interface Window {
        appConfig?: Record<string, any>;
        activeUserId?: string;
        userInfo?: UserInfo[];
    }
}

export let API_URL: string | null = null;
export let USER_ID: string | null = null;

export let config = {
    API_URL: "http://localhost:8000/api",
    ENABLE_AUTH: false,
};

export function setApiUrl(url: string | null) {
    if (url) {
        API_URL = url.includes('/api') ? url : `${url}/api`;
    }
}

export function setEnvData(configData: Record<string, any>) {
    if (configData) {
        config.API_URL = configData.API_URL || "";
        config.ENABLE_AUTH = configData.ENABLE_AUTH || false;
    }
}

export function getConfigData() {
    if (!config.API_URL || !config.ENABLE_AUTH) {
        // Check if window.appConfig exists
        if (window.appConfig) {
            setEnvData(window.appConfig);
        }
    }

    return { ...config };
}
export async function getUserInfo(): Promise<UserInfo[]> {
    try {
        const response = await fetch("/.auth/me");
        console.log("Fetching user info from: ", "/.auth/me");
        console.log("Response ", response);
        if (!response.ok) {
            console.log(
                "No identity provider found. Access to chat will be blocked."
            );
            return [];
        }
        const payload = await response.json();
        return payload;
    } catch (e) {
        return [];
    }
}
export function getApiUrl() {
    if (!API_URL) {
        // Check if window.appConfig exists
        if (window.appConfig && window.appConfig.API_URL) {
            setApiUrl(window.appConfig.API_URL);
        }
    }

    if (!API_URL) {
        console.info('API URL not yet configured');
        return null;
    }

    return API_URL;
}

export function getUserId(): string {
    // USER_ID = window.userInfo && window.userInfo[0] && window.userInfo[0].user_id ? window.userInfo[0].user_id : null;
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
export const toBoolean = (value: any): boolean => {
    if (typeof value !== 'string') {
        return false;
    }
    return value.trim().toLowerCase() === 'true';
};
export default {
    setApiUrl,
    getApiUrl,
    toBoolean,
    getUserId,
    getConfigData,
    setEnvData,
    config,
    USER_ID,
    API_URL
};