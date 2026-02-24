import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/** Format cents to currency string (INR) */
export function formatCurrency(cents: number, currency: string = "INR"): string {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency,
        minimumFractionDigits: 2,
    }).format(cents / 100);
}

/** Format ISO date string to readable format */
export function formatDate(date: string | Date | null | undefined): string {
    if (!date) return "—";
    const d = typeof date === "string" && !date.endsWith("Z") ? new Date(`${date}Z`) : new Date(date);
    return new Intl.DateTimeFormat("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(d);
}

/** Format ISO date string to relative time */
export function timeAgo(date: string | Date): string {
    const d = typeof date === "string" && !date.endsWith("Z") ? new Date(`${date}Z`) : new Date(date);
    const seconds = Math.floor((Date.now() - d.getTime()) / 1000);
    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

/** Map entity status to Tailwind color classes */
export function statusColor(status: string): string {
    switch (status?.toUpperCase()) {
        case "DRAFT":
        case "PENDING":
        case "PENDING_APPROVAL":
        case "DISPUTED":
        case "PARTIALLY_RECEIVED":
            return "warning";
        case "APPROVED":
        case "ACTIVE":
        case "MATCHED":
        case "FULFILLED":
        case "PAID":
        case "PASS":
            return "success";
        case "REJECTED":
        case "BLOCKED":
        case "EXCEPTION":
        case "FAIL":
        case "MISMATCHED":
        case "CANCELLED":
            return "destructive";
        case "ISSUED":
        case "ACKNOWLEDGED":
        case "UPLOADED":
        case "SUBMITTED":
            return "accent";
        case "OPEN":
        case "UNDER_REVIEW":
            return "info";
        case "AWARDED":
            return "success";
        case "CLOSED":
        case "ARCHIVED":
            return "secondary";
        default:
            return "secondary";
    }
}

/** Export data as CSV file download */
export function exportCSV(headers: string[], rows: string[][], filename: string) {
    const csvContent = [
        headers.join(","),
        ...rows.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")),
    ].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
}
