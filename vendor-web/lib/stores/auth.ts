"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi, api } from "@/lib/api/client";
import type { User, Vendor } from "@/types/models";

interface AuthState {
    user: User | null;
    vendor: Vendor | null;
    accessToken: string | null;
    refreshToken: string | null;
    isHydrated: boolean;

    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
    setHydrated: () => void;
    fetchVendorProfile: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            user: null,
            vendor: null,
            accessToken: null,
            refreshToken: null,
            isHydrated: false,

            setHydrated: () => set({ isHydrated: true }),

            login: async (email: string, password: string) => {
                const { data } = await authApi.post("/auth/login", { email, password });

                // Store tokens for interceptor
                localStorage.setItem("vendor_access_token", data.access_token);
                localStorage.setItem("vendor_refresh_token", data.refresh_token);

                // Fetch user profile
                const { data: profile } = await authApi.get("/auth/me", {
                    headers: { Authorization: `Bearer ${data.access_token}` },
                });

                // Verify vendor role
                if (profile.role !== "vendor") {
                    localStorage.removeItem("vendor_access_token");
                    localStorage.removeItem("vendor_refresh_token");
                    throw new Error("Access denied. This portal is for vendor accounts only.");
                }

                set({
                    user: profile,
                    accessToken: data.access_token,
                    refreshToken: data.refresh_token,
                });

                // Fetch vendor profile after login
                try {
                    const { data: vendorData } = await api.get("/vendors/me", {
                        headers: { Authorization: `Bearer ${data.access_token}` },
                    });
                    set({ vendor: vendorData });
                } catch {
                    // Vendor profile fetch is best-effort
                }
            },

            logout: () => {
                localStorage.removeItem("vendor_access_token");
                localStorage.removeItem("vendor_refresh_token");
                set({ user: null, vendor: null, accessToken: null, refreshToken: null });
                if (typeof window !== "undefined") window.location.href = "/login";
            },

            fetchVendorProfile: async () => {
                try {
                    const { data } = await api.get("/vendors/me");
                    set({ vendor: data });
                } catch {
                    // silent
                }
            },
        }),
        {
            name: "svpms-vendor-auth",
            partialize: (state) => ({
                user: state.user,
                vendor: state.vendor,
                accessToken: state.accessToken,
                refreshToken: state.refreshToken,
            }),
            onRehydrateStorage: () => (state) => {
                state?.setHydrated();
            },
        }
    )
);
