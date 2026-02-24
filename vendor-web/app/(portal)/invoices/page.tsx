"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Plus, Receipt } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { invoiceService } from "@/lib/api/invoices";
import { formatCurrency, formatDate, exportCSV } from "@/lib/utils";
import type { Invoice } from "@/types/models";

const STATUS_FILTERS = ["ALL", "UPLOADED", "MATCHED", "EXCEPTION", "DISPUTED", "APPROVED", "PAID"];

export default function InvoicesPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [data, setData] = useState<Invoice[]>([]);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState(searchParams.get("status") || "ALL");

    const fetchData = async (p: number, s: string) => {
        setLoading(true);
        try {
            const params: Record<string, any> = { page: p, per_page: 20 };
            if (s !== "ALL") params.status = s;
            const res = await invoiceService.list(params);
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
            ["Invoice #", "PO #", "Status", "Total", "Currency", "Invoice Date", "Match Status"],
            data.map((inv) => [
                inv.invoice_number,
                inv.po_number || "—",
                inv.status,
                (inv.total_cents / 100).toFixed(2),
                inv.currency,
                formatDate(inv.invoice_date),
                inv.match_status || "—",
            ]),
            `invoices-${new Date().toISOString().split("T")[0]}.csv`
        );
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Invoices</h1>
                    <p className="text-muted-foreground">Upload and track your invoices</p>
                </div>
                <Link href="/invoices/upload">
                    <Button>
                        <Plus className="h-4 w-4 mr-2" /> Upload Invoice
                    </Button>
                </Link>
            </div>

            <div className="flex flex-wrap gap-2">
                {STATUS_FILTERS.map((s) => (
                    <Button
                        key={s}
                        variant={status === s ? "default" : "outline"}
                        size="sm"
                        onClick={() => { setStatus(s); setPage(1); }}
                    >
                        {s === "ALL" ? "All" : s}
                    </Button>
                ))}
            </div>

            <DataTable
                columns={[
                    { header: "Invoice #", accessorKey: "invoice_number", sortable: true },
                    { header: "PO #", cell: (row) => row.po_number || "—" },
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
                        header: "Date",
                        cell: (row) => formatDate(row.invoice_date || row.created_at),
                        sortable: true,
                        accessorKey: "created_at",
                    },
                    {
                        header: "Match",
                        cell: (row) => row.match_status ? <StatusBadge status={row.match_status} /> : "—",
                    },
                ]}
                data={data}
                loading={loading}
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
                onRowClick={(row) => router.push(`/invoices/${row.id}`)}
                emptyMessage="No invoices found."
                onExport={data.length > 0 ? handleExport : undefined}
            />
        </div>
    );
}
