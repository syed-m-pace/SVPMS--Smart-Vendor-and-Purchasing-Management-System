"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/shared/DataTable";
import { receiptService } from "@/lib/api/services";
import { formatDate } from "@/lib/utils";
import type { Receipt } from "@/types/models";

export default function ReceiptsPage() {
    const [receipts, setReceipts] = useState<Receipt[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    useEffect(() => {
        receiptService.list({ page }).then((r) => { setReceipts(r.data); setTotalPages(r.pagination.total_pages); }).catch(() => { }).finally(() => setLoading(false));
    }, [page]);

    const columns = [
        { header: "Receipt #", cell: (r: Receipt) => <span className="font-mono font-medium">{r.receipt_number}</span> },
        { header: "PO ID", cell: (r: Receipt) => <span className="font-mono text-xs">{r.po_id.slice(0, 8)}…</span> },
        { header: "Received", cell: (r: Receipt) => formatDate(r.received_at) },
        { header: "Notes", cell: (r: Receipt) => <span className="text-muted-foreground">{r.notes || "—"}</span> },
    ];

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Receipts</h1>
                <p className="text-muted-foreground mt-1">Goods receipt tracking</p>
            </div>
            <DataTable columns={columns} data={receipts} loading={loading} page={page} totalPages={totalPages} onPageChange={setPage} />
        </div>
    );
}
