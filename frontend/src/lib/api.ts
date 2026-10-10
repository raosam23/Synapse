import { useAuthStore } from "@/store/authStore";

const backend_url = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const apiRequest = async <T>(
    path: string,
    option?: {
        method?: string,
        body?: unknown,
        headers?: Record<string, string>,
    }
) : Promise<T> => {
    const { method = "GET", body, headers = {} } = option || {};
    const url = `${backend_url}${path}`;
    const response = await fetch(url, {
        method,
        credentials: "include",
        body: body ? JSON.stringify(body): undefined,
        headers: {
            "Content-Type": "application/json",
            ...headers,
        },
    });
    if (!response.ok) {
        if (response.status === 401) {
            useAuthStore.getState().clearAuth();
        }
        throw new Error(`API error: ${response.status} ${response.statusText}`)
    }
    return response.json() as Promise<T>;
};

export const api = {
    get: <T>(path: string, option?: { headers?: Record<string, string> }) => apiRequest<T>(path, { method: "GET", ...option }),
    post: <T>(path: string, body: unknown, option? : { headers?: Record<string, string> }) => apiRequest<T>(path, { method: "POST", body, ...option }),
    put: <T>(path: string, body: unknown, option? : { headers?: Record<string, string> }) => apiRequest<T>(path, { method: "PUT", body, ...option }),
    delete: <T>(path: string, option? : { headers?: Record<string, string> }) => apiRequest<T>(path, { method: "DELETE", ...option }),
};