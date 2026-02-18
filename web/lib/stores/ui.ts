"use client";

import { create } from "zustand";

interface UIState {
    sidebarOpen: boolean;
    refreshNotifications: number;
    toggleSidebar: () => void;
    setSidebarOpen: (open: boolean) => void;
    triggerRefreshNotifications: () => void;
}

export const useUIStore = create<UIState>()((set) => ({
    sidebarOpen: true,
    refreshNotifications: 0,
    toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
    setSidebarOpen: (open) => set({ sidebarOpen: open }),
    triggerRefreshNotifications: () => set((s) => ({ refreshNotifications: s.refreshNotifications + 1 })),
}));
