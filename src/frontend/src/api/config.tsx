// src/config.js

import { UserInfo, claim } from "@/models";


declare global {
    interface Window {
        appConfig?: Record<string, any>;
        activeUserId?: string;
        userInfo?: UserInfo;
    }
}

export let API_URL: string | null = null;
export let USER_ID: string | null = null;
export let USER_INFO: UserInfo | null = null;

export let config = {
    API_URL: "http://localhost:8000/api",
    ENABLE_AUTH: false,
};

export function setApiUrl(url: string | null) {
    if (url) {
        API_URL = url.includes('/api') ? url : `${url}/api`;
    }
}
export function setUserInfoGlobal(userInfo: UserInfo | null) {
    if (userInfo) {
        USER_ID = userInfo.user_id || null;
        USER_INFO = userInfo;
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
export async function getUserInfo(): Promise<UserInfo> {
    try {
        const response = await fetch("/.auth/me");
        if (!response.ok) {
            console.log(
                "No identity provider found. Access to chat will be blocked."
            );
            return {} as UserInfo;
        }
        const payload = await response.json();
        const userInfo: UserInfo = {
            access_token: payload[0].access_token || "",
            expires_on: payload[0].expires_on || "",
            id_token: payload[0].id_token || "",
            provider_name: payload[0].provider_name || "",
            user_claims: payload[0].user_claims || [],
            user_email: payload[0].user_id || "",
            user_first_last_name: payload[0].user_claims?.find((claim: claim) => claim.typ === 'name')?.val || "",
            user_id: payload[0].user_claims?.find((claim: claim) => claim.typ === 'http://schemas.microsoft.com/identity/claims/objectidentifier')?.val || '',
        };
        return userInfo;
    } catch (e) {
        return {} as UserInfo;
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
export function getUserInfoGlobal() {
    if (!USER_INFO) {
        // Check if window.userInfo exists
        if (window.userInfo) {
            setUserInfoGlobal(window.userInfo);
        }
    }

    if (!USER_INFO) {
        console.info('User info not yet configured');
        return null;
    }

    return USER_INFO;
}

export function getUserId(): string {
    // USER_ID = getUserInfoGlobal()?.user_id || null;
    if (!USER_ID) {
        USER_ID = getUserInfoGlobal()?.user_id || null;
    }
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
    console.log('headerBuilder: Using user ID:', userId);
    let defaultHeaders = {
        "x-ms-client-principal-id": String(userId) || "",  // Custom header
    };
    console.log('headerBuilder: Created headers:', defaultHeaders);
    return {
        ...defaultHeaders,
        ...(headers ? headers : {})
    };
}

/**
 * Initialize team on the backend - takes about 20 seconds
 * @returns Promise with team initialization response
 */
export async function initializeTeam(): Promise<{
    status: string;
    team_id: string;
}> {
    const apiUrl = getApiUrl();
    if (!apiUrl) {
        throw new Error('API URL not configured');
    }

    const headers = headerBuilder({
        'Content-Type': 'application/json',
    });

    console.log('initializeTeam: Starting team initialization...');
    
    try {
        const response = await fetch(`${apiUrl}/init_team`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('initializeTeam: Team initialization completed:', data);
        
        // Validate the expected response format
        if (data.status !== 'Request started successfully' || !data.team_id) {
            throw new Error('Invalid response format from init_team endpoint');
        }
        
        return data;
    } catch (error) {
        console.error('initializeTeam: Error initializing team:', error);
        throw error;
    }
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
    API_URL,
    initializeTeam 
};