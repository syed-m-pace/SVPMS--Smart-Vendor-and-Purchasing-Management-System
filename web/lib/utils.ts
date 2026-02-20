import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/** Format cents to currency string (INR) */
export function formatCurrency(cents: number): string {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2,
    }).format(cents / 100);
}

/** Format ISO date string to readable format */
export function formatDate(date: string | Date): string {
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
    const seconds = Math.floor(
        (Date.now() - d.getTime()) / 1000
    );
    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}
