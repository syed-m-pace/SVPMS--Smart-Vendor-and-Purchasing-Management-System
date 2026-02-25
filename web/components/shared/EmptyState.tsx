"use client";

import { Inbox } from "lucide-react";

interface EmptyStateProps {
    icon?: React.ElementType;
    title?: string;
    description?: string;
    children?: React.ReactNode;
}

export function EmptyState({
    icon: Icon = Inbox,
    title = "No items found",
    description = "There are no items to display right now.",
    children,
}: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 rounded-full bg-muted p-4">
                <Icon className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-1">{title}</h3>
            <p className="text-sm text-muted-foreground max-w-sm">{description}</p>
            {children && <div className="mt-4">{children}</div>}
        </div>
    );
}
