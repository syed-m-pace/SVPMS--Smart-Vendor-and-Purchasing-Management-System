"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { poService } from "@/lib/api/purchase-orders";
import { vendorService } from "@/lib/api/vendors";
import { formatCurrency, formatDate, timeAgo } from "@/lib/utils";
import type { PurchaseOrder, PurchaseOrderReady, Vendor } from "@/types/models";
import { toast } from "sonner";
import { isAxiosError } from "axios";

export default function PurchaseOrdersPage() {
    const router = useRouter();
    const [pos, setPos] = useState<PurchaseOrder[]>([]);
    const [readyItems, setReadyItems] = useState<PurchaseOrderReady[]>([]);
    const [vendors, setVendors] = useState<Vendor[]>([]);
    const [vendorByPr, setVendorByPr] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(true);
    const [readyLoading, setReadyLoading] = useState(true);
    const [issuingPrId, setIssuingPrId] = useState<string | null>(null);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    const getErrorMessage = (error: unknown, fallback: string) => {
        if (isAxiosError(error)) {
            const detail = error.response?.data?.detail;
            if (typeof detail === "string") return detail;
        }
        return fallback;
    };

    const loadPOs = useCallback(async () => {
        setLoading(true);
        try {
            const r = await poService.list({ page });
            setPos(r.data);
            setTotalPages(r.pagination.total_pages);
        } catch {
            toast.error("Failed to load purchase orders");
        } finally {
            setLoading(false);
        }
    }, [page]);

    const loadReadyItems = useCallback(async () => {
        setReadyLoading(true);
        try {
            const r = await poService.ready({ page: 1, limit: 50 });
            setReadyItems(r.data);
        } catch {
            toast.error("Failed to load approved PRs ready for PO");
        } finally {
            setReadyLoading(false);
        }
    }, []);

    const loadActiveVendors = useCallback(async () => {
        try {
            const r = await vendorService.list({ page: 1, limit: 100, status: "ACTIVE" });
            setVendors(r.data);
            if (r.data.length > 0) {
                const firstVendor = r.data[0].id;
                setVendorByPr((prev) => {
                    const next = { ...prev };
                    readyItems.forEach((item) => {
                        if (!next[item.pr_id]) next[item.pr_id] = firstVendor;
                    });
                    return next;
                });
            }
        } catch {
            toast.error("Failed to load active vendors");
        }
    }, [readyItems]);

    useEffect(() => {
        void loadPOs();
    }, [loadPOs]);

    useEffect(() => {
        void loadReadyItems();
        void loadActiveVendors();
    }, [loadActiveVendors, loadReadyItems]);

    useEffect(() => {
        if (vendors.length === 0) return;
        const firstVendor = vendors[0].id;
        setVendorByPr((prev) => {
            const next = { ...prev };
            readyItems.forEach((item) => {
                if (!next[item.pr_id]) next[item.pr_id] = firstVendor;
            });
            return next;
        });
    }, [vendors, readyItems]);

    async function issuePO(item: PurchaseOrderReady) {
        const selectedVendorId = vendorByPr[item.pr_id];
        if (!selectedVendorId) {
            toast.error("Select a vendor first");
            return;
        }

        setIssuingPrId(item.pr_id);
        try {
            const po = await poService.create({
                pr_id: item.pr_id,
                vendor_id: selectedVendorId,
            });
            toast.success(`Created ${po.po_number}`);
            setReadyItems((prev) => prev.filter((r) => r.pr_id !== item.pr_id));
            setPos((prev) => [po, ...prev]);
        } catch (error: unknown) {
            toast.error(getErrorMessage(error, "Failed to issue PO"));
        } finally {
            setIssuingPrId(null);
        }
    }

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

            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Approved PRs Ready to Issue</CardTitle>
                </CardHeader>
                <CardContent>
                    {readyLoading ? (
                        <p className="text-sm text-muted-foreground">Loading ready queue...</p>
                    ) : readyItems.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No approved PRs are waiting for PO creation.</p>
                    ) : (
                        <div className="space-y-3">
                            {readyItems.map((item) => (
                                <div key={item.pr_id} className="rounded-lg border p-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                                    <div>
                                        <p className="font-mono font-medium">{item.pr_number}</p>
                                        <p className="text-sm text-muted-foreground">
                                            {formatCurrency(item.total_cents)}
                                            {item.approved_at ? ` • Approved ${formatDate(item.approved_at)}` : ""}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                                        <select
                                            className="h-9 rounded-md border bg-background px-2 text-sm"
                                            value={vendorByPr[item.pr_id] || ""}
                                            onChange={(e) =>
                                                setVendorByPr((prev) => ({
                                                    ...prev,
                                                    [item.pr_id]: e.target.value,
                                                }))
                                            }
                                        >
                                            <option value="" disabled>
                                                Select vendor
                                            </option>
                                            {vendors.map((v) => (
                                                <option key={v.id} value={v.id}>
                                                    {v.legal_name}
                                                </option>
                                            ))}
                                        </select>
                                        <Button
                                            size="sm"
                                            onClick={() => issuePO(item)}
                                            disabled={!vendorByPr[item.pr_id] || issuingPrId === item.pr_id}
                                        >
                                            {issuingPrId === item.pr_id ? "Issuing..." : "Issue PO"}
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            <DataTable
                columns={columns}
                data={pos}
                loading={loading}
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
                onRowClick={(po) => router.push(`/purchase-orders/${po.id}`)}
            />
        </div>
    );
}
