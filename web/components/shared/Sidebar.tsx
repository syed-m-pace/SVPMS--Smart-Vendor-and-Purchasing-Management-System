"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    Users,
    ShoppingCart,
    FileText,
    Receipt,
    CheckSquare,
    Wallet,
    AlertTriangle,
    Package,
    BarChart2,
    ChevronLeft,
    ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/stores/auth";
import { useUIStore } from "@/lib/stores/ui";
import type { UserRole } from "@/types/models";

interface NavItem {
    label: string;
    href: string;
    icon: React.ElementType;
    roles?: UserRole[];
}

const navItems: NavItem[] = [
    { label: "Dashboard", href: "/", icon: LayoutDashboard },
    { label: "Purchase Requests", href: "/purchase-requests", icon: FileText },
    { label: "Approvals", href: "/approvals", icon: CheckSquare },
    { label: "Purchase Orders", href: "/purchase-orders", icon: ShoppingCart },
    { label: "Receipts", href: "/receipts", icon: Receipt },
    { label: "Invoices", href: "/invoices", icon: Package },
    { label: "Vendors", href: "/vendors", icon: Users },
    { label: "Budgets", href: "/budgets", icon: Wallet },
    {
        label: "Analytics",
        href: "/analytics",
        icon: BarChart2,
        roles: ["admin", "manager", "finance_head", "cfo"],
    },
    {
        label: "Exceptions",
        href: "/exceptions",
        icon: AlertTriangle,
        roles: ["admin", "manager", "finance_head", "cfo"],
    },
];

export function Sidebar() {
    const pathname = usePathname();
    const user = useAuthStore((s) => s.user);
    const { sidebarOpen, toggleSidebar } = useUIStore();

    const visibleItems = navItems.filter(
        (item) => !item.roles || (user && item.roles.includes(user.role))
    );

    return (
        <aside
            className={cn(
                "fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-sidebar text-sidebar-foreground transition-all duration-300",
                sidebarOpen ? "w-[260px]" : "w-16"
            )}
        >
            {/* Logo */}
            <div className="flex h-16 items-center justify-between border-b border-white/10 px-4">
                {sidebarOpen && (
                    <Link href="/" className="flex items-center gap-2">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-white font-bold text-sm">
                            S
                        </div>
                        <span className="text-lg font-bold tracking-tight">SVPMS</span>
                    </Link>
                )}
                <button
                    onClick={toggleSidebar}
                    className="rounded-md p-1.5 hover:bg-white/10 transition-colors"
                >
                    {sidebarOpen ? (
                        <ChevronLeft className="h-4 w-4" />
                    ) : (
                        <ChevronRight className="h-4 w-4" />
                    )}
                </button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
                {visibleItems.map((item) => {
                    const isActive =
                        pathname === item.href ||
                        (item.href !== "/" && pathname.startsWith(item.href));
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                                isActive
                                    ? "bg-accent text-white shadow-md shadow-accent/25"
                                    : "text-sidebar-foreground/70 hover:bg-white/8 hover:text-sidebar-foreground"
                            )}
                            title={!sidebarOpen ? item.label : undefined}
                        >
                            <item.icon className="h-5 w-5 shrink-0" />
                            {sidebarOpen && <span>{item.label}</span>}
                        </Link>
                    );
                })}
            </nav>

            {/* User section */}
            {user && sidebarOpen && (
                <div className="border-t border-white/10 p-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/20 text-accent text-xs font-bold">
                            {user.first_name?.[0]}
                            {user.last_name?.[0]}
                        </div>
                        <div className="flex-1 truncate">
                            <p className="text-sm font-medium truncate">
                                {user.first_name} {user.last_name}
                            </p>
                            <p className="text-xs text-sidebar-foreground/50 truncate capitalize">
                                {user.role.replace("_", " ")}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </aside>
    );
}
