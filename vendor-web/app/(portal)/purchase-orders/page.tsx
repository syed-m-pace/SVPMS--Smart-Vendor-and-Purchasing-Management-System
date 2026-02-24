"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ShoppingCart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { poService } from "@/lib/api/purchase-orders";
import { formatCurrency, formatDate, exportCSV } from "@/lib/utils";
import type { PurchaseOrder } from "@/types/models";

const STATUS_FILTERS = ["ALL", "ISSUED", "ACKNOWLEDGED", "PARTIALLY_RECEIVED", "FULFILLED", "CLOSED"];

export default function PurchaseOrdersPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [data, setData] = useState<PurchaseOrder[]>([]);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState(searchParams.get("status") || "ALL");

    const fetchData = async (p: number, s: string) => {
        setLoading(true);
        try {
            const params: Record<string, any> = { page: p, per_page: 20 };
            if (s !== "ALL") params.status = s;
            const res = await poService.list(params);
            setData(res.data);
            setTotalPages(res.pagination.total_pages);
        } catch {
            setData([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData(page, status);
    }, [page, status]);

    const handleExport = () => {
        exportCSV(
            ["PO Number", "Status", "Total", "Currency", "Issued Date", "Delivery Date"],
            data.map((po) => [
                po.po_number,
                po.status,
                (po.total_cents / 100).toFixed(2),
                po.currency,
                formatDate(po.issued_at),
                formatDate(po.expected_delivery_date),
            ]),
            `purchase-orders-${new Date().toISOString().split("T")[0]}.csv`
        );
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Purchase Orders</h1>
                <p className="text-muted-foreground">View and manage your incoming orders</p>
            </div>

            {/* Status Filters */}
            <div className="flex flex-wrap gap-2">
                {STATUS_FILTERS.map((s) => (
                    <Button
                        key={s}
                        variant={status === s ? "default" : "outline"}
                        size="sm"
                        onClick={() => { setStatus(s); setPage(1); }}
                    >
                        {s === "ALL" ? "All" : s.replace(/_/g, " ")}
                    </Button>
                ))}
            </div>

            <DataTable
                columns={[
                    { header: "PO Number", accessorKey: "po_number", sortable: true },
                    {
                        header: "Status",
                        cell: (row) => <StatusBadge status={row.status} />,
                    },
                    {
                        header: "Total",
                        cell: (row) => formatCurrency(row.total_cents, row.currency),
                        sortable: true,
                        accessorKey: "total_cents",
                    },
                    {
                        header: "Issued",
                        cell: (row) => formatDate(row.issued_at),
                        sortable: true,
                        accessorKey: "issued_at",
                    },
                    {
                        header: "Delivery Date",
                        cell: (row) => formatDate(row.expected_delivery_date),
                    },
                ]}
                data={data}
                loading={loading}
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
                onRowClick={(row) => router.push(`/purchase-orders/${row.id}`)}
                emptyMessage="No purchase orders found."
                onExport={data.length > 0 ? handleExport : undefined}
            />
        </div>
    );
}
