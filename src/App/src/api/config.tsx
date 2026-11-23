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

export function resolveApiAssetUrl(url: string): string {
   if (!url) {
       return url;
   }
   const marker = "/api/v4/images/";
   const idx = url.indexOf(marker);
   if (idx === -1) {
       return url;
   }
   const path = url.slice(idx); // drop any scheme+host before the image path
   const apiUrl = getApiUrl();
   if (apiUrl && /^https?:\/\//i.test(apiUrl)) {
       try {
           return new URL(apiUrl).origin + path;
       } catch {
           return path;
       }
   }
   return path;
}

export function getUserInfoGlobal() {
    if (!USER_INFO) {
        // Check if window.userInfo exists
        if (window.userInfo) {
            setUserInfoGlobal(window.userInfo);
        }
    }

    if (!USER_INFO) {
        return null;
    }

    return USER_INFO;
}

export function getUserId(): string {
    if (!USER_ID) {
        USER_ID = getUserInfoGlobal()?.user_id || null;
    }
    const userId = USER_ID ?? "00000000-0000-0000-0000-000000000000";
    return userId;
}

const TOKEN_REFRESH_MARGIN_SECONDS = 300;
let tokenRefreshPromise: Promise<string> | null = null;

function getTokenExpiry(token: string): number {
    try {
        const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
        return typeof payload.exp === 'number' ? payload.exp : 0;
    } catch {
        return 0;
    }
}

function isTokenValid(token: string, marginSeconds = 0): boolean {
    return !!token && getTokenExpiry(token) - marginSeconds > Date.now() / 1000;
}

async function refreshIdToken(currentToken: string): Promise<string> {
    try {
        await fetch('/.auth/refresh');
    } catch {
        // Ignore: fall back to the token currently held by App Service Authentication
    }
    const refreshed = await getUserInfo();
    if (isTokenValid(refreshed.id_token)) {
        window.userInfo = refreshed;
        setUserInfoGlobal(refreshed);
        return refreshed.id_token;
    }
    if (isTokenValid(currentToken)) {
        return currentToken;
    }
    // The sign-in session can no longer be refreshed silently; sign in again.
    window.location.href = `/.auth/login/aad?post_login_redirect_uri=${encodeURIComponent(window.location.pathname + window.location.search)}`;
    return '';
}

/**
 * Returns the Entra ID token from App Service Authentication (/.auth/me) for
 * calling the backend API, refreshing it shortly before it expires.
 * Returns an empty string when App Service Authentication is not configured.
 */
export async function getIdToken(): Promise<string> {
    const token = getUserInfoGlobal()?.id_token || '';
    if (!token || isTokenValid(token, TOKEN_REFRESH_MARGIN_SECONDS)) {
        return token;
    }
    if (!tokenRefreshPromise) {
        tokenRefreshPromise = refreshIdToken(token).finally(() => {
            tokenRefreshPromise = null;
        });
    }
    return tokenRefreshPromise;
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
};