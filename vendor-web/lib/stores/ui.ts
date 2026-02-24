"use client";

import { create } from "zustand";

interface UIState {
    sidebarOpen: boolean;
    refreshCounter: number;
    toggleSidebar: () => void;
    setSidebarOpen: (open: boolean) => void;
    triggerRefresh: () => void;
}

export const useUIStore = create<UIState>()((set) => ({
    sidebarOpen: true,
    refreshCounter: 0,
    toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
    setSidebarOpen: (open) => set({ sidebarOpen: open }),
    triggerRefresh: () => set((s) => ({ refreshCounter: s.refreshCounter + 1 })),
}));
