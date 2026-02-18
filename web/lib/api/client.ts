import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://svpms-be-gcloud-325948496969.asia-south1.run.app";

export const api = axios.create({
    baseURL: `${API_BASE}/api/v1`,
    timeout: 30000,
    headers: { "Content-Type": "application/json" },
});

export const authApi = axios.create({
    baseURL: API_BASE,
    timeout: 30000,
    headers: { "Content-Type": "application/json" },
});

/* ── Attach token on every request ── */
api.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("access_token");
        if (token) config.headers.Authorization = `Bearer ${token}`;
    }
    // Idempotency key for mutations
    if (["post", "put", "patch"].includes(config.method?.toLowerCase() || "")) {
        config.headers["Idempotency-Key"] = `${Date.now()}-${Math.random()
            .toString(36)
            .slice(2)}`;
    }
    return config;
});

/* ── Handle 401 → auto-refresh ── */
api.interceptors.response.use(
    (res) => res,
    async (error) => {
        const original = error.config;
        if (error.response?.status === 401 && !original._retry) {
            original._retry = true;
            try {
                const refreshToken = localStorage.getItem("refresh_token");
                if (!refreshToken) throw new Error("No refresh token");
                const { data } = await authApi.post("/auth/refresh", {
                    refresh_token: refreshToken,
                });
                localStorage.setItem("access_token", data.access_token);
                if (data.refresh_token)
                    localStorage.setItem("refresh_token", data.refresh_token);
                original.headers.Authorization = `Bearer ${data.access_token}`;
                return api(original);
            } catch {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
                if (typeof window !== "undefined") window.location.href = "/login";
                return Promise.reject(error);
            }
        }
        return Promise.reject(error);
    }
);
