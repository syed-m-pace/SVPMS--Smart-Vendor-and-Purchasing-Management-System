"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bell, LogOut, Menu } from "lucide-react";
import { useAuthStore } from "@/lib/stores/auth";
import { useUIStore } from "@/lib/stores/ui";
import { Button } from "@/components/ui/button";
import { approvalService } from "@/lib/api/services";

export function Navbar() {
    const user = useAuthStore((s) => s.user);
    const logout = useAuthStore((s) => s.logout);
    const toggleSidebar = useUIStore((s) => s.toggleSidebar);
    const [pendingCount, setPendingCount] = useState(0);

    useEffect(() => {
        approvalService.listPending().then((r) => setPendingCount(r.pagination.total)).catch(() => { });
    }, []);

    return (
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-card/80 backdrop-blur-sm px-6">
            <div className="flex items-center gap-4">
                <button
                    onClick={toggleSidebar}
                    className="rounded-md p-2 hover:bg-muted transition-colors lg:hidden"
                >
                    <Menu className="h-5 w-5" />
                </button>
            </div>

            <div className="flex items-center gap-3">
                {/* Notification bell — links to approvals */}
                <Link href="/approvals">
                    <Button variant="ghost" size="icon" className="relative">
                        <Bell className="h-5 w-5 text-muted-foreground" />
                        {pendingCount > 0 && (
                            <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] text-white font-bold">
                                {pendingCount}
                            </span>
                        )}
                    </Button>
                </Link>

                {/* User dropdown */}
                {user && (
                    <div className="flex items-center gap-3 border-l pl-3">
                        <div className="hidden sm:block text-right">
                            <p className="text-sm font-medium">
                                {user.first_name} {user.last_name}
                            </p>
                            <p className="text-xs text-muted-foreground capitalize">
                                {user.role.replace("_", " ")}
                            </p>
                        </div>
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={logout}
                            title="Logout"
                        >
                            <LogOut className="h-4 w-4 text-muted-foreground" />
                        </Button>
                    </div>
                )}
            </div>
        </header>
    );
}

