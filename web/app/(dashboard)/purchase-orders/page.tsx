"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { poService } from "@/lib/api/purchase-orders";
import { vendorService } from "@/lib/api/vendors";
import { rfqService } from "@/lib/api/rfqs";
import { formatCurrency, formatDate, timeAgo } from "@/lib/utils";
import type { PurchaseOrder, PurchaseOrderReady, Vendor, RFQ } from "@/types/models";
import { toast } from "sonner";
import { isAxiosError } from "axios";

export default function PurchaseOrdersPage() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState("all");

    // All POs state
    const [pos, setPos] = useState<PurchaseOrder[]>([]);
    const [readyItems, setReadyItems] = useState<PurchaseOrderReady[]>([]);
    const [vendors, setVendors] = useState<Vendor[]>([]);
    const [vendorByPr, setVendorByPr] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(true);
    const [readyLoading, setReadyLoading] = useState(true);
    const [issuingPrId, setIssuingPrId] = useState<string | null>(null);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    // Acknowledgments state
    const [ackPos, setAckPos] = useState<PurchaseOrder[]>([]);
    const [ackLoading, setAckLoading] = useState(false);
    const [ackPage, setAckPage] = useState(1);
    const [ackTotalPages, setAckTotalPages] = useState(1);

    // RFQs state
    const [rfqs, setRfqs] = useState<RFQ[]>([]);
    const [rfqLoading, setRfqLoading] = useState(false);
    const [rfqPage, setRfqPage] = useState(1);
    const [rfqTotalPages, setRfqTotalPages] = useState(1);

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

    const loadAckPOs = useCallback(async () => {
        setAckLoading(true);
        try {
            const r = await poService.list({ page: ackPage, status: "ACKNOWLEDGED" });
            setAckPos(r.data);
            setAckTotalPages(r.pagination.total_pages);
        } catch {
            toast.error("Failed to load acknowledged purchase orders");
        } finally {
            setAckLoading(false);
        }
    }, [ackPage]);

    const loadRFQs = useCallback(async () => {
        setRfqLoading(true);
        try {
            const r = await rfqService.list({ page: rfqPage });
            setRfqs(r.data);
            setRfqTotalPages(r.pagination.total_pages);
        } catch {
            toast.error("Failed to load RFQs");
        } finally {
            setRfqLoading(false);
        }
    }, [rfqPage]);

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
        } catch {
            toast.error("Failed to load active vendors");
        }
    }, []);

    // Load data based on active tab
    useEffect(() => {
        if (activeTab === "all") {
            void loadPOs();
        } else if (activeTab === "acknowledgments") {
            void loadAckPOs();
        } else if (activeTab === "rfqs") {
            void loadRFQs();
        }
    }, [activeTab, loadPOs, loadAckPOs, loadRFQs]);

    // Load static lookups
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

    const poColumns = [
        { header: "PO Number", cell: (po: PurchaseOrder) => <span className="font-mono font-medium">{po.po_number}</span> },
        { header: "Vendor", cell: (po: PurchaseOrder) => <span>{po.vendor_name || "—"}</span> },
        { header: "Status", cell: (po: PurchaseOrder) => <StatusBadge status={po.status} /> },
        { header: "Amount", cell: (po: PurchaseOrder) => <span className="font-mono">{formatCurrency(po.total_cents)}</span> },
        { header: "Issued", cell: (po: PurchaseOrder) => <span className="text-muted-foreground">{po.issued_at ? timeAgo(po.issued_at) : "—"}</span> },
    ];

    const ackColumns = [
        { header: "PO Number", cell: (po: PurchaseOrder) => <span className="font-mono font-medium">{po.po_number}</span> },
        { header: "Vendor", cell: (po: PurchaseOrder) => <span>{po.vendor_name || "—"}</span> },
        { header: "Amount", cell: (po: PurchaseOrder) => <span className="font-mono">{formatCurrency(po.total_cents)}</span> },
        { header: "Expected Delivery", cell: (po: PurchaseOrder) => <span className="font-medium text-blue-600">{po.expected_delivery_date ? formatDate(po.expected_delivery_date) : "Not specified"}</span> },
        { header: "Updated", cell: (po: PurchaseOrder) => <span className="text-muted-foreground">{po.updated_at ? timeAgo(po.updated_at) : "—"}</span> },
    ];

    const rfqColumns = [
        { header: "RFQ Number", cell: (rfq: RFQ) => <span className="font-mono font-medium">{rfq.rfq_number}</span> },
        { header: "Status", cell: (rfq: RFQ) => <StatusBadge status={rfq.status} /> },
        { header: "Deadline", cell: (rfq: RFQ) => <span className="font-medium">{rfq.deadline ? formatDate(rfq.deadline) : "—"}</span> },
        { header: "Created", cell: (rfq: RFQ) => <span className="text-muted-foreground">{rfq.created_at ? timeAgo(rfq.created_at) : "—"}</span> },
    ];

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Purchase Orders & RFQs</h1>
                    <p className="text-muted-foreground mt-1">Manage PO lifecycle and Quotations</p>
                </div>
                {activeTab === "rfqs" && (
                    <Button onClick={() => router.push("/purchase-orders/rfqs/new")}>
                        Issue New RFQ
                    </Button>
                )}
            </div>

            <Tabs defaultValue="all" value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="grid w-full grid-cols-3 max-w-md">
                    <TabsTrigger value="all">All POs</TabsTrigger>
                    <TabsTrigger value="acknowledgments">Acknowledgments</TabsTrigger>
                    <TabsTrigger value="rfqs">RFQs</TabsTrigger>
                </TabsList>

                <TabsContent value="all" className="space-y-6 mt-6">
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
                                                    <option value="" disabled>Select vendor</option>
                                                    {vendors.map((v) => (
                                                        <option key={v.id} value={v.id}>{v.legal_name}</option>
                                                    ))}
                                                </select>
                                                <Button size="sm" onClick={() => issuePO(item)} disabled={!vendorByPr[item.pr_id] || issuingPrId === item.pr_id}>
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
                        columns={poColumns}
                        data={pos}
                        loading={loading}
                        page={page}
                        totalPages={totalPages}
                        onPageChange={setPage}
                        onRowClick={(po) => router.push(`/purchase-orders/${po.id}`)}
                    />
                </TabsContent>

                <TabsContent value="acknowledgments" className="mt-6">
                    <DataTable
                        columns={ackColumns}
                        data={ackPos}
                        loading={ackLoading}
                        page={ackPage}
                        totalPages={ackTotalPages}
                        onPageChange={setAckPage}
                        onRowClick={(po) => router.push(`/purchase-orders/${po.id}`)}
                    />
                </TabsContent>

                <TabsContent value="rfqs" className="mt-6">
                    <DataTable
                        columns={rfqColumns}
                        data={rfqs}
                        loading={rfqLoading}
                        page={rfqPage}
                        totalPages={rfqTotalPages}
                        onPageChange={setRfqPage}
                        onRowClick={(rfq) => router.push(`/purchase-orders/rfqs/${rfq.id}`)}
                    />
                </TabsContent>
            </Tabs>
        </div>
    );
}
