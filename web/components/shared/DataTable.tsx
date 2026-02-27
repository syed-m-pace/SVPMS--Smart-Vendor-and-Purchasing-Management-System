"use client";

import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Column<T> {
    header: string;
    accessorKey?: keyof T;
    cell?: (row: T) => React.ReactNode;
    className?: string;
}

interface DataTableProps<T> {
    columns: Column<T>[];
    data: T[];
    loading?: boolean;
    page?: number;
    totalPages?: number;
    onPageChange?: (page: number) => void;
    onRowClick?: (row: T) => void;
    emptyMessage?: string;
    paginationLoading?: boolean;
}

export function DataTable<T extends Record<string, any>>({
    columns,
    data,
    loading,
    page = 1,
    totalPages = 1,
    onPageChange,
    onRowClick,
    emptyMessage = "No data found.",
    paginationLoading = false,
}: DataTableProps<T>) {
    if (loading) {
        return (
            <div className="rounded-xl border bg-card">
                <div className="p-8 text-center">
                    <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" />
                    <p className="mt-3 text-sm text-muted-foreground">Loading...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="rounded-xl border bg-card overflow-hidden">
            <div className="overflow-x-auto relative">
                {/* Pagination loading overlay */}
                {paginationLoading && (
                    <div className="absolute inset-0 bg-card/60 backdrop-blur-[1px] z-10 flex items-center justify-center">
                        <div className="flex items-center gap-2 bg-background/90 px-4 py-2 rounded-lg shadow-sm border">
                            <Loader2 className="h-4 w-4 animate-spin text-accent" />
                            <span className="text-sm text-muted-foreground">Loading...</span>
                        </div>
                    </div>
                )}
                <table className="w-full">
                    <thead>
                        <tr className="border-b bg-muted/50">
                            {columns.map((col, i) => (
                                <th
                                    key={i}
                                    className={cn(
                                        "px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground",
                                        col.className
                                    )}
                                >
                                    {col.header}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {data.length === 0 ? (
                            <tr>
                                <td
                                    colSpan={columns.length}
                                    className="px-4 py-12 text-center text-sm text-muted-foreground"
                                >
                                    {emptyMessage}
                                </td>
                            </tr>
                        ) : (
                            data.map((row, rowIdx) => (
                                <tr
                                    key={rowIdx}
                                    onClick={() => onRowClick?.(row)}
                                    className={cn(
                                        "border-b transition-colors hover:bg-muted/30",
                                        onRowClick && "cursor-pointer"
                                    )}
                                >
                                    {columns.map((col, colIdx) => (
                                        <td
                                            key={colIdx}
                                            className={cn("px-4 py-3 text-sm", col.className)}
                                        >
                                            {col.cell
                                                ? col.cell(row)
                                                : col.accessorKey
                                                    ? String(row[col.accessorKey] ?? "—")
                                                    : "—"}
                                        </td>
                                    ))}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between border-t px-4 py-3">
                    <div className="flex items-center gap-2">
                        <p className="text-sm text-muted-foreground">
                            Page {page} of {totalPages}
                        </p>
                        {paginationLoading && (
                            <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                        )}
                    </div>
                    <div className="flex gap-1">
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={page <= 1 || paginationLoading}
                            onClick={() => onPageChange?.(page - 1)}
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={page >= totalPages || paginationLoading}
                            onClick={() => onPageChange?.(page + 1)}
                        >
                            <ChevronRight className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
