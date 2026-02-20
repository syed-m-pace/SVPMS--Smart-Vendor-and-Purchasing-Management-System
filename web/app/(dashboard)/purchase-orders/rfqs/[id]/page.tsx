"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { formatCurrency, formatDate, timeAgo } from "@/lib/utils";
import { rfqService } from "@/lib/api/rfqs";
import { poService } from "@/lib/api/purchase-orders";
import { vendorService } from "@/lib/api/vendors";
import type { RFQ, RFQBid, Vendor } from "@/types/models";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Clock, Users, CheckCircle, Package } from "lucide-react";
import { toast } from "sonner";
import { isAxiosError } from "axios";

export default function RfqDetailsPage() {
    const params = useParams();
    const router = useRouter();
    const rfqId = params.id as string;

    const [rfq, setRfq] = useState<RFQ | null>(null);
    const [vendors, setVendors] = useState<Record<string, Vendor>>({});
    const [loading, setLoading] = useState(true);
    const [awarding, setAwarding] = useState<string | null>(null);

    const getErrorMessage = (error: unknown, fallback: string) => {
        if (isAxiosError(error)) {
            const detail = error.response?.data?.detail;
            if (typeof detail === "string") return detail;
        }
        return fallback;
    };

    const fetchDetails = async () => {
        setLoading(true);
        try {
            const rfqData = await rfqService.get(rfqId);
            setRfq(rfqData);

            // Fetch vendor details for the bids
            if (rfqData.bids && rfqData.bids.length > 0) {
                const uniqueVendorIds = Array.from(new Set(rfqData.bids.map((b: RFQBid) => b.vendor_id)));
                await fetchVendors(uniqueVendorIds);
            }
        } catch (error) {
            toast.error(getErrorMessage(error, "Failed to load RFQ details"));
            router.push("/purchase-orders");
        } finally {
            setLoading(false);
        }
    };

    const fetchVendors = async (vendorIds: string[]) => {
        try {
            // we will fetch all vendors for simplicity unless list grows huge
            const vResponse = await vendorService.list({ limit: 1000 });
            const vendorMap: Record<string, Vendor> = {};
            vResponse.data.forEach((v: Vendor) => {
                if (vendorIds.includes(v.id)) {
                    vendorMap[v.id] = v;
                }
            });
            setVendors(vendorMap);
        } catch (error) {
            console.error("Failed to load vendors", error);
        }
    };

    useEffect(() => {
        if (rfqId) {
            fetchDetails();
        }
    }, [rfqId]);

    const handleAward = async (bid: RFQBid) => {
        if (!rfq?.pr_id) {
            toast.error("Original PR is missing from this RFQ");
            return;
        }

        setAwarding(bid.id);
        try {
            const po = await poService.create({
                pr_id: rfq.pr_id,
                vendor_id: bid.vendor_id,
            });
            toast.success(`Successfully awarded PO to ${vendors[bid.vendor_id]?.legal_name || "vendor"}: ${po.po_number}`);
            router.push(`/purchase-orders/${po.id}`);
        } catch (error) {
            toast.error(getErrorMessage(error, "Failed to award PO"));
            setAwarding(null);
        }
    };

    if (loading) {
        return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading RFQ Details...</div>;
    }

    if (!rfq) return null;

    const totalQuantity = rfq.line_items?.reduce((sum, item) => sum + item.quantity, 0) || 0;
    const isClosed = rfq.status === "CLOSED" || (rfq.deadline ? new Date(rfq.deadline) < new Date() : false);

    return (
        <div className="space-y-6 max-w-5xl mx-auto">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.push("/purchase-orders")}>
                    <ArrowLeft className="h-5 w-5" />
                </Button>
                <div>
                    <div className="flex items-center gap-3">
                        <h1 className="text-3xl font-bold tracking-tight">{rfq.title}</h1>
                        <StatusBadge status={rfq.status} />
                    </div>
                    <p className="text-muted-foreground mt-1 font-mono">{rfq.rfq_number}</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                            <Package className="h-5 w-5 text-muted-foreground" />
                            Line Items ({totalQuantity} total qty)
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="border rounded-md divide-y">
                            {rfq.line_items?.map((item) => (
                                <div key={item.id} className="p-4 flex flex-col md:flex-row gap-4 justify-between items-start">
                                    <div>
                                        <p className="font-medium text-base">{item.description}</p>
                                        {item.specifications && (
                                            <p className="text-sm text-muted-foreground mt-1 bg-muted/50 p-2 rounded">
                                                {item.specifications}
                                            </p>
                                        )}
                                    </div>
                                    <div className="whitespace-nowrap px-3 py-1 bg-primary/10 text-primary font-semibold rounded-full text-sm">
                                        Qty: {item.quantity}
                                    </div>
                                </div>
                            ))}
                            {(!rfq.line_items || rfq.line_items.length === 0) && (
                                <div className="p-4 text-center text-muted-foreground">No line items specified</div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">Details</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <p className="text-sm font-medium text-muted-foreground mb-1">Created</p>
                                <p className="font-medium">{formatDate(rfq.created_at)}</p>
                            </div>
                            <div>
                                <p className="text-sm font-medium text-muted-foreground mb-1">Deadline</p>
                                <p className={`font-medium flex items-center gap-2 ${isClosed ? "text-destructive" : ""}`}>
                                    <Clock className="h-4 w-4" />
                                    {rfq.deadline ? formatDate(rfq.deadline) : "—"}
                                    {isClosed && <span className="text-xs bg-destructive/10 px-2 py-0.5 rounded-full">Passed</span>}
                                </p>
                            </div>
                            <div>
                                <p className="text-sm font-medium text-muted-foreground mb-1">Total Bids</p>
                                <p className="font-medium flex items-center gap-2">
                                    <Users className="h-4 w-4" />
                                    {rfq.bids?.length || 0}
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        Vendor Bids
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {!rfq.bids || rfq.bids.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg">
                            <p>No bids have been submitted yet.</p>
                            <p className="text-sm mt-1">Vendors will be notified and can submit bids from their mobile app.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {rfq.bids.sort((a: RFQBid, b: RFQBid) => a.total_cents - b.total_cents).map((bid: RFQBid) => {
                                const vendor = vendors[bid.vendor_id];
                                return (
                                    <div key={bid.id} className="flex flex-col md:flex-row justify-between items-start md:items-center p-4 border rounded-xl gap-4 hover:border-primary/50 transition-colors">
                                        <div className="space-y-1">
                                            <p className="font-semibold text-lg">{vendor?.legal_name || "Loading Vendor..."}</p>
                                            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                                                <span>Submitted {timeAgo(bid.submitted_at)}</span>
                                                {bid.delivery_days && (
                                                    <span className="flex items-center gap-1">
                                                        <Clock className="h-3.5 w-3.5" />
                                                        {bid.delivery_days} days delivery
                                                    </span>
                                                )}
                                            </div>
                                            {bid.notes && (
                                                <p className="mt-2 text-sm max-w-2xl bg-muted/30 p-2 rounded border">{bid.notes}</p>
                                            )}
                                        </div>

                                        <div className="flex flex-col items-end gap-3 min-w-[140px]">
                                            <div className="text-right">
                                                <p className="text-2xl font-bold text-primary">{formatCurrency(bid.total_cents)}</p>
                                            </div>

                                            {isClosed ? (
                                                <Button
                                                    onClick={() => handleAward(bid)}
                                                    disabled={awarding !== null}
                                                    className="w-full gap-2 shadow-md"
                                                    variant="default"
                                                >
                                                    {awarding === bid.id ? "Awarding..." : "Award PO"}
                                                    <CheckCircle className="h-4 w-4" />
                                                </Button>
                                            ) : (
                                                <div className="text-xs text-muted-foreground text-center bg-muted px-2 py-1 rounded w-full">
                                                    Available after deadline
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </CardContent>
            </Card>

        </div>
    );
}
