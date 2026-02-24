"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, ShoppingCart, Gavel, Receipt, Banknote, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { timeAgo } from "@/lib/utils";
import type { AppNotification } from "@/types/models";

function getStoredNotifications(): AppNotification[] {
    if (typeof window === "undefined") return [];
    try {
        return JSON.parse(localStorage.getItem("vendor_notifications") || "[]");
    } catch {
        return [];
    }
}

function setStoredNotifications(notifications: AppNotification[]) {
    localStorage.setItem("vendor_notifications", JSON.stringify(notifications));
}

function getIcon(type: string) {
    switch (type) {
        case "po": return ShoppingCart;
        case "rfq": return Gavel;
        case "invoice": return Receipt;
        case "payment": return Banknote;
        default: return Bell;
    }
}

export default function NotificationsPage() {
    const router = useRouter();
    const [notifications, setNotifications] = useState<AppNotification[]>(getStoredNotifications);

    const handleClick = (n: AppNotification) => {
        // Mark as read
        const updated = notifications.map((item) =>
            item.id === n.id ? { ...item, read: true } : item
        );
        setNotifications(updated);
        setStoredNotifications(updated);

        // Navigate to related entity
        if (n.entity_id) {
            switch (n.type) {
                case "po": router.push(`/purchase-orders/${n.entity_id}`); break;
                case "rfq": router.push(`/rfqs/${n.entity_id}`); break;
                case "invoice":
                case "payment": router.push(`/invoices/${n.entity_id}`); break;
                default: break;
            }
        }
    };

    const handleClearAll = () => {
        setNotifications([]);
        setStoredNotifications([]);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Notifications</h1>
                    <p className="text-muted-foreground">Your recent notifications and updates</p>
                </div>
                {notifications.length > 0 && (
                    <Button variant="outline" size="sm" onClick={handleClearAll}>
                        <Trash2 className="h-4 w-4 mr-2" /> Clear All
                    </Button>
                )}
            </div>

            {notifications.length === 0 ? (
                <EmptyState
                    icon={Bell}
                    title="No notifications"
                    description="You're all caught up! Notifications about POs, RFQs, and invoices will appear here."
                />
            ) : (
                <div className="space-y-2">
                    {notifications.map((n) => {
                        const Icon = getIcon(n.type);
                        return (
                            <Card
                                key={n.id}
                                className={`p-4 cursor-pointer hover:shadow-sm transition-shadow ${
                                    !n.read ? "border-l-4 border-l-accent" : ""
                                }`}
                                onClick={() => handleClick(n)}
                            >
                                <div className="flex items-start gap-3">
                                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted">
                                        <Icon className="h-4 w-4 text-muted-foreground" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className={`text-sm ${!n.read ? "font-semibold" : "font-medium"}`}>
                                            {n.title}
                                        </p>
                                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                                            {n.body}
                                        </p>
                                    </div>
                                    <span className="text-xs text-muted-foreground shrink-0">
                                        {timeAgo(n.created_at)}
                                    </span>
                                </div>
                            </Card>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
