"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, Menu, ChevronRight } from "lucide-react";
import { useAuthStore } from "@/lib/stores/auth";
import { useUIStore } from "@/lib/stores/ui";
import { Button } from "@/components/ui/button";

const breadcrumbMap: Record<string, string> = {
    "/": "Dashboard",
    "/purchase-orders": "Purchase Orders",
    "/rfqs": "RFQs",
    "/rfqs/bids": "Bid History",
    "/invoices": "Invoices",
    "/invoices/upload": "Upload Invoice",
    "/contracts": "Contracts",
    "/analytics": "Analytics",
    "/notifications": "Notifications",
    "/profile": "Profile",
};

export function Navbar() {
    const user = useAuthStore((s) => s.user);
    const toggleSidebar = useUIStore((s) => s.toggleSidebar);
    const pathname = usePathname();

    // Build breadcrumb segments
    const segments = pathname.split("/").filter(Boolean);
    const breadcrumbs: { label: string; href: string }[] = [{ label: "Home", href: "/" }];
    let currentPath = "";
    for (const seg of segments) {
        currentPath += `/${seg}`;
        const label = breadcrumbMap[currentPath];
        if (label) {
            breadcrumbs.push({ label, href: currentPath });
        } else if (seg !== "[id]" && !seg.match(/^[0-9a-f-]{36}$/)) {
            breadcrumbs.push({ label: seg.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()), href: currentPath });
        }
    }

    return (
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-card/80 backdrop-blur-sm px-6">
            <div className="flex items-center gap-4">
                <button
                    onClick={toggleSidebar}
                    className="rounded-md p-2 hover:bg-muted transition-colors lg:hidden"
                >
                    <Menu className="h-5 w-5" />
                </button>

                {/* Breadcrumbs */}
                <nav className="hidden sm:flex items-center gap-1 text-sm">
                    {breadcrumbs.map((bc, i) => (
                        <span key={bc.href} className="flex items-center gap-1">
                            {i > 0 && <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                            {i === breadcrumbs.length - 1 ? (
                                <span className="font-medium text-foreground">{bc.label}</span>
                            ) : (
                                <Link href={bc.href} className="text-muted-foreground hover:text-foreground transition-colors">
                                    {bc.label}
                                </Link>
                            )}
                        </span>
                    ))}
                </nav>
            </div>

            <div className="flex items-center gap-3">
                <Link href="/notifications">
                    <Button variant="ghost" size="icon" className="relative">
                        <Bell className="h-5 w-5 text-muted-foreground" />
                    </Button>
                </Link>

                {user && (
                    <div className="hidden sm:flex items-center gap-3 border-l pl-3">
                        <div className="text-right">
                            <p className="text-sm font-medium">
                                {user.first_name} {user.last_name}
                            </p>
                            <p className="text-xs text-muted-foreground">Vendor</p>
                        </div>
                    </div>
                )}
            </div>
        </header>
    );
}
