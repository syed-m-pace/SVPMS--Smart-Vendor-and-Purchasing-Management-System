"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/shared/Sidebar";
import { Navbar } from "@/components/shared/Navbar";
import { useAuthStore } from "@/lib/stores/auth";
import { useUIStore } from "@/lib/stores/ui";
import { cn } from "@/lib/utils";

export default function PortalLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const { user, isHydrated } = useAuthStore();
    const sidebarOpen = useUIStore((s) => s.sidebarOpen);

    useEffect(() => {
        if (isHydrated && !user) {
            router.replace("/login");
        }
    }, [isHydrated, user, router]);

    if (!isHydrated) {
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" />
            </div>
        );
    }

    if (!user) return null;

    return (
        <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div
                className={cn(
                    "flex flex-1 flex-col transition-all duration-300",
                    sidebarOpen ? "ml-[260px]" : "ml-16"
                )}
            >
                <Navbar />
                <main className="flex-1 overflow-y-auto p-6 bg-background">
                    <div className="animate-fade-in">{children}</div>
                </main>
            </div>
        </div>
    );
}
