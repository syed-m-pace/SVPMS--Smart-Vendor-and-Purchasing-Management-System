"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Trophy, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { rfqService } from "@/lib/api/rfqs";
import { useAuthStore } from "@/lib/stores/auth";
import { formatCurrency, formatDate } from "@/lib/utils";
import { toast } from "sonner";
import type { RFQ, RFQBid } from "@/types/models";

export default function RFQDetailPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();
    const vendor = useAuthStore((s) => s.vendor);
    const [rfq, setRfq] = useState<RFQ | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        rfqService.get(id).then(setRfq).catch(() => toast.error("Failed to load RFQ")).finally(() => setLoading(false));
    }, [id]);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" />
            </div>
        );
    }

    if (!rfq) {
        return (
            <div className="text-center py-20">
                <p className="text-muted-foreground">RFQ not found</p>
                <Button variant="outline" className="mt-4" onClick={() => router.push("/rfqs")}>
                    <ArrowLeft className="h-4 w-4 mr-2" /> Back
                </Button>
            </div>
        );
    }

    const myBid = rfq.bids?.find((b) => vendor && b.vendor_id === vendor.id);
    const isAwarded = rfq.status === "AWARDED" && rfq.awarded_vendor_id === vendor?.id;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => router.push("/rfqs")}>
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold">{rfq.title}</h1>
                        <p className="text-muted-foreground">{rfq.rfq_number}</p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <StatusBadge status={rfq.status} />
                    {rfq.status === "OPEN" && (
                        <Link href={`/rfqs/${id}/bid`}>
                            <Button>{myBid ? "Update Bid" : "Submit Bid"}</Button>
                        </Link>
                    )}
                </div>
            </div>

            {/* Award Banner */}
            {isAwarded && (
                <Card className="p-4 border-success bg-success/5">
                    <div className="flex items-center gap-3">
                        <Trophy className="h-6 w-6 text-success" />
                        <div className="flex-1">
                            <p className="font-semibold text-success">Congratulations! Your bid was awarded</p>
                            <p className="text-sm text-muted-foreground">A Purchase Order has been created from this RFQ.</p>
                        </div>
                        {rfq.awarded_po_id && (
                            <Link href={`/purchase-orders/${rfq.awarded_po_id}`}>
                                <Button variant="outline" size="sm">
                                    View PO <ExternalLink className="h-3 w-3 ml-1" />
                                </Button>
                            </Link>
                        )}
                    </div>
                </Card>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="p-5">
                    <h3 className="font-semibold mb-4">RFQ Details</h3>
                    <div className="space-y-3">
                        <InfoRow label="RFQ Number" value={rfq.rfq_number} />
                        <InfoRow label="Status" value={<StatusBadge status={rfq.status} />} />
                        <InfoRow label="Budget" value={rfq.budget_cents ? formatCurrency(rfq.budget_cents) : "—"} />
                        <InfoRow label="Deadline" value={formatDate(rfq.deadline)} />
                        <InfoRow label="Created" value={formatDate(rfq.created_at)} />
                    </div>
                    {rfq.description && (
                        <div className="mt-4 pt-4 border-t">
                            <p className="text-xs text-muted-foreground mb-1">Description</p>
                            <p className="text-sm">{rfq.description}</p>
                        </div>
                    )}
                </Card>

                {/* Your Bid */}
                <Card className="p-5">
                    <h3 className="font-semibold mb-4">
                        {myBid ? "Your Submitted Bid" : "No Bid Submitted"}
                    </h3>
                    {myBid ? (
                        <div className="space-y-3">
                            <InfoRow label="Bid Amount" value={formatCurrency(myBid.total_cents)} />
                            <InfoRow label="Lead Time" value={`${myBid.delivery_days || "—"} days`} />
                            <InfoRow label="Submitted" value={formatDate(myBid.submitted_at)} />
                            {myBid.notes && (
                                <div className="mt-2 pt-2 border-t">
                                    <p className="text-xs text-muted-foreground mb-1">Notes</p>
                                    <p className="text-sm">{myBid.notes}</p>
                                </div>
                            )}
                            {isAwarded && (
                                <div className="mt-2 p-2 rounded bg-success/10 text-success text-sm font-medium text-center">
                                    Bid Awarded
                                </div>
                            )}
                        </div>
                    ) : rfq.status === "OPEN" ? (
                        <div className="text-center py-6">
                            <p className="text-sm text-muted-foreground mb-3">You haven&apos;t submitted a bid yet</p>
                            <Link href={`/rfqs/${id}/bid`}>
                                <Button>Submit Bid</Button>
                            </Link>
                        </div>
                    ) : (
                        <p className="text-sm text-muted-foreground text-center py-6">
                            This RFQ is no longer accepting bids
                        </p>
                    )}
                </Card>
            </div>

            {/* Line Items */}
            {rfq.line_items && rfq.line_items.length > 0 && (
                <Card className="p-5">
                    <h3 className="font-semibold mb-4">Line Items</h3>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b bg-muted/50">
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">#</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">Description</th>
                                    <th className="px-4 py-3 text-right text-xs font-medium uppercase text-muted-foreground">Quantity</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">Unit</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">Specs</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rfq.line_items.map((item, i) => (
                                    <tr key={item.id} className="border-b">
                                        <td className="px-4 py-3 text-sm">{i + 1}</td>
                                        <td className="px-4 py-3 text-sm">{item.description}</td>
                                        <td className="px-4 py-3 text-sm text-right">{item.quantity}</td>
                                        <td className="px-4 py-3 text-sm">{item.unit || "—"}</td>
                                        <td className="px-4 py-3 text-sm">{item.specifications || "—"}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}
        </div>
    );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
    return (
        <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{label}</span>
            <span className="text-sm font-medium">{value}</span>
        </div>
    );
}
