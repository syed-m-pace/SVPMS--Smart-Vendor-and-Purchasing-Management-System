"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, ArrowUpDown, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Column<T> {
    header: string;
    accessorKey?: keyof T;
    cell?: (row: T) => React.ReactNode;
    className?: string;
    sortable?: boolean;
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
    onExport?: () => void;
    exportLabel?: string;
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
    onExport,
    exportLabel = "Export CSV",
}: DataTableProps<T>) {
    const [sortKey, setSortKey] = useState<keyof T | null>(null);
    const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

    const handleSort = (key: keyof T) => {
        if (sortKey === key) {
            setSortDir(sortDir === "asc" ? "desc" : "asc");
        } else {
            setSortKey(key);
            setSortDir("asc");
        }
    };

    const sortedData = sortKey
        ? [...data].sort((a, b) => {
              const aVal = a[sortKey];
              const bVal = b[sortKey];
              if (aVal == null) return 1;
              if (bVal == null) return -1;
              const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
              return sortDir === "asc" ? cmp : -cmp;
          })
        : data;

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
            {/* Export button */}
            {onExport && data.length > 0 && (
                <div className="flex justify-end px-4 pt-3">
                    <Button variant="outline" size="sm" onClick={onExport}>
                        <Download className="h-4 w-4 mr-1" />
                        {exportLabel}
                    </Button>
                </div>
            )}

            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="border-b bg-muted/50">
                            {columns.map((col, i) => (
                                <th
                                    key={i}
                                    className={cn(
                                        "px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground",
                                        col.sortable && col.accessorKey && "cursor-pointer select-none hover:text-foreground",
                                        col.className
                                    )}
                                    onClick={() => col.sortable && col.accessorKey && handleSort(col.accessorKey)}
                                >
                                    <span className="flex items-center gap-1">
                                        {col.header}
                                        {col.sortable && col.accessorKey && (
                                            <ArrowUpDown className={cn("h-3 w-3", sortKey === col.accessorKey && "text-accent")} />
                                        )}
                                    </span>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {sortedData.length === 0 ? (
                            <tr>
                                <td
                                    colSpan={columns.length}
                                    className="px-4 py-12 text-center text-sm text-muted-foreground"
                                >
                                    {emptyMessage}
                                </td>
                            </tr>
                        ) : (
                            sortedData.map((row, rowIdx) => (
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
                    <p className="text-sm text-muted-foreground">
                        Page {page} of {totalPages}
                    </p>
                    <div className="flex gap-1">
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={page <= 1}
                            onClick={() => onPageChange?.(page - 1)}
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={page >= totalPages}
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
