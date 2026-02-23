"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { invoiceService } from "@/lib/api/invoices";
import { formatCurrency, timeAgo } from "@/lib/utils";
import type { Invoice } from "@/types/models";

export default function InvoicesPage() {
    const router = useRouter();
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    useEffect(() => {
        invoiceService.list({ page }).then((r) => { setInvoices(r.data); setTotalPages(r.pagination.total_pages); }).catch(() => { }).finally(() => setLoading(false));
    }, [page]);

    const columns = [
        { header: "Invoice #", cell: (inv: Invoice) => <span className="font-mono font-medium">{inv.invoice_number}</span> },
        { header: "Vendor", cell: (inv: Invoice) => <span>{inv.vendor_name || "—"}</span> },
        { header: "Status", cell: (inv: Invoice) => <StatusBadge status={inv.status} /> },
        { header: "Match", cell: (inv: Invoice) => inv.match_status ? <StatusBadge status={inv.match_status} /> : <span className="text-muted-foreground">—</span> },
        { header: "Amount", cell: (inv: Invoice) => <span className="font-mono">{formatCurrency(inv.total_cents)}</span> },
        { header: "Created", cell: (inv: Invoice) => <span className="text-muted-foreground">{timeAgo(inv.created_at)}</span> },
    ];

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Invoices</h1>
                <p className="text-muted-foreground mt-1">Track and manage invoices</p>
            </div>
            <DataTable columns={columns} data={invoices} loading={loading} page={page} totalPages={totalPages} onPageChange={setPage} onRowClick={(inv) => router.push(`/invoices/${inv.id}`)} />
        </div>
    );
}
