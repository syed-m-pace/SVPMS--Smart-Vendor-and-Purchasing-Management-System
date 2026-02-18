"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { poService } from "@/lib/api/purchase-orders";
import { formatCurrency, timeAgo } from "@/lib/utils";
import type { PurchaseOrder } from "@/types/models";

export default function PurchaseOrdersPage() {
    const router = useRouter();
    const [pos, setPos] = useState<PurchaseOrder[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    useEffect(() => {
        poService.list({ page }).then((r) => { setPos(r.data); setTotalPages(r.pagination.total_pages); }).catch(() => { }).finally(() => setLoading(false));
    }, [page]);

    const columns = [
        { header: "PO Number", cell: (po: PurchaseOrder) => <span className="font-mono font-medium">{po.po_number}</span> },
        { header: "Status", cell: (po: PurchaseOrder) => <StatusBadge status={po.status} /> },
        { header: "Amount", cell: (po: PurchaseOrder) => <span className="font-mono">{formatCurrency(po.total_cents)}</span> },
        { header: "Issued", cell: (po: PurchaseOrder) => <span className="text-muted-foreground">{po.issued_at ? timeAgo(po.issued_at) : "—"}</span> },
    ];

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Purchase Orders</h1>
                <p className="text-muted-foreground mt-1">Track purchase orders</p>
            </div>
            <DataTable columns={columns} data={pos} loading={loading} page={page} totalPages={totalPages} onPageChange={setPage} onRowClick={(po) => router.push(`/purchase-orders/${po.id}`)} />
        </div>
    );
}
