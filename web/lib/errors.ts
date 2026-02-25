import { isAxiosError } from "axios";

/**
 * Extract a user-friendly error message from any caught error.
 * Handles Axios errors with structured backend responses,
 * generic Error objects, and unknown types.
 */
export function extractErrorMessage(
    error: unknown,
    fallback = "Something went wrong. Please try again."
): string {
    if (isAxiosError(error)) {
        const data = error.response?.data;
        // FastAPI detail string
        if (typeof data?.detail === "string") return data.detail;
        // FastAPI detail array (validation errors)
        if (Array.isArray(data?.detail)) {
            return data.detail.map((e: { msg: string }) => e.msg).join(", ");
        }
        // Nested error message
        if (typeof data?.error?.message === "string") return data.error.message;
        // HTTP status-based messages
        const status = error.response?.status;
        if (status === 401) return "Session expired. Please log in again.";
        if (status === 403) return "You don't have permission to do this.";
        if (status === 404) return "The requested resource was not found.";
        if (status === 429) return "Too many requests. Please slow down.";
        if (status && status >= 500)
            return "Server error. Please try again later.";
        // Network error
        if (error.code === "ERR_NETWORK")
            return "Network error. Check your connection.";
        if (error.code === "ECONNABORTED") return "Request timed out.";
    }

    if (error instanceof Error) return error.message;

    return fallback;
}
