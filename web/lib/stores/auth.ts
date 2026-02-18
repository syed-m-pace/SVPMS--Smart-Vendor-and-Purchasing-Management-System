"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi } from "@/lib/api/client";
import type { User } from "@/types/models";

interface AuthState {
    user: User | null;
    accessToken: string | null;
    refreshToken: string | null;
    isHydrated: boolean;

    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
    setHydrated: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            accessToken: null,
            refreshToken: null,
            isHydrated: false,

            setHydrated: () => set({ isHydrated: true }),

            login: async (email: string, password: string) => {
                const { data } = await authApi.post("/auth/login", { email, password });

                // Decode JWT to get user info
                const payload = JSON.parse(atob(data.access_token.split(".")[1]));

                // Store tokens in localStorage for interceptor
                localStorage.setItem("access_token", data.access_token);
                localStorage.setItem("refresh_token", data.refresh_token);

                // Fetch full user profile
                const { data: profile } = await authApi.get("/auth/me", {
                    headers: { Authorization: `Bearer ${data.access_token}` },
                });

                set({
                    user: profile,
                    accessToken: data.access_token,
                    refreshToken: data.refresh_token,
                });
            },

            logout: () => {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
                set({ user: null, accessToken: null, refreshToken: null });
                if (typeof window !== "undefined") window.location.href = "/login";
            },
        }),
        {
            name: "svpms-auth",
            partialize: (state) => ({
                user: state.user,
                accessToken: state.accessToken,
                refreshToken: state.refreshToken,
            }),
            onRehydrateStorage: () => (state) => {
                state?.setHydrated();
            },
        }
    )
);
