import {
  headerBuilder,
  getApiUrl,
  ensureFreshToken,
  reauthSilently,
} from "./config";

// Helper function to build URL with query parameters
const buildUrl = (url: string, params?: Record<string, any>): string => {
  if (!params) return url;

  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  return queryString ? `${url}?${queryString}` : url;
};

// Fetch with Authentication Headers
const fetchWithAuth = async (
  url: string,
  method: string = "GET",
  body: BodyInit | null = null,
) => {
  // Serialize the body ONCE so it can be replayed on a 401 retry.
  const isForm = body instanceof FormData;
  const hasBody = body !== null && body !== undefined;
  const serializedBody: BodyInit | null = isForm
    ? (body as FormData)
    : hasBody
      ? JSON.stringify(body)
      : null;
  // Build request options from the CURRENT auth state. Called before the
  // first attempt and again after a forced refresh so the retry carries the
  // freshly-minted token, never the dead one.
  const buildOptions = (): RequestInit => {
    const headers: Record<string, string> = { ...headerBuilder() };
    if (isForm) delete headers["Content-Type"];
    else headers["Content-Type"] = "application/json";
    return { method, headers, body: serializedBody || undefined };
  };

  const apiUrl = getApiUrl();
  const finalUrl = `${apiUrl}${url}`;

  try {
    await ensureFreshToken(); // proactive: refresh only if near expiry
    let response = await fetch(finalUrl, buildOptions());

    if (response.status === 401) {
      await ensureFreshToken(Number.POSITIVE_INFINITY);
      response = await fetch(finalUrl, buildOptions());

      if (response.status === 401) {
        const errorText = await response.text().catch(() => "");
        reauthSilently();
        throw new Error(errorText || "Session expired — re-authenticating");
      }
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || "Something went wrong");
    }

    const isJson = response.headers
      .get("content-type")
      ?.includes("application/json");
    const responseData = isJson ? await response.json() : null;
    return responseData;
  } catch (error) {
    console.info("API Error:", (error as Error).message);
    throw error;
  }
};

// Vanilla Fetch without Auth for Login
const fetchWithoutAuth = async (
  url: string,
  method: string = "POST",
  body: BodyInit | null = null,
) => {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const options: RequestInit = {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  };

  try {
    const apiUrl = getApiUrl();
    const response = await fetch(`${apiUrl}${url}`, options);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || "Login failed");
    }
    const isJson = response.headers
      .get("content-type")
      ?.includes("application/json");
    return isJson ? await response.json() : null;
  } catch (error) {
    console.log("Login Error:", (error as Error).message);
    throw error;
  }
};

// Authenticated requests (with token) and login (without token)
export const apiClient = {
  get: (url: string, config?: { params?: Record<string, any> }) => {
    const finalUrl = buildUrl(url, config?.params);
    return fetchWithAuth(finalUrl, "GET");
  },
  post: (url: string, body?: any) => fetchWithAuth(url, "POST", body),
  put: (url: string, body?: any) => fetchWithAuth(url, "PUT", body),
  patch: (url: string, body?: any) => fetchWithAuth(url, "PATCH", body),
  delete: (url: string) => fetchWithAuth(url, "DELETE"),
  upload: (url: string, formData: FormData) =>
    fetchWithAuth(url, "POST", formData),
  login: (url: string, body?: any) => fetchWithoutAuth(url, "POST", body), // For login without auth

  /**
   * Raw streaming POST — returns the Response object for SSE consumption.
   * Does NOT parse JSON; caller reads response.body as a ReadableStream.
   */
  stream: async (
    url: string,
    body?: any,
    signal?: AbortSignal,
  ): Promise<Response> => {
    const apiUrl = getApiUrl();
    const finalUrl = `${apiUrl}${url}`;
    const serializedBody = body ? JSON.stringify(body) : undefined;

    // Rebuild options from the CURRENT auth state so a replay after a forced
    // refresh carries the fresh token, never the dead one.
    const buildOptions = (): RequestInit => ({
      method: "POST",
      headers: { ...headerBuilder(), "Content-Type": "application/json" },
      body: serializedBody,
      signal,
    });

    await ensureFreshToken(); // proactive: refresh only if near expiry
    let response = await fetch(finalUrl, buildOptions());

    // The EasyAuth token expires mid-session (~1h). SSE has NO retry layer
    // above this call (fetchWithAuth is bypassed), so recover HERE exactly as
    // fetchWithAuth does: force a refresh and replay ONCE. Without this, an
    // expired token forced a full page reload to resume streaming
    // (chat/message/stream) — the observed failure.
    if (response.status === 401) {
      await ensureFreshToken(Number.POSITIVE_INFINITY); // force, ignore skew
      response = await fetch(finalUrl, buildOptions());
      if (response.status === 401) {
        const errorText = await response.text().catch(() => "");
        reauthSilently();
        throw new Error(errorText || "Session expired — re-authenticating");
      }
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || "Stream request failed");
    }
    return response;
  },
};
