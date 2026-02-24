"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Check, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { poService } from "@/lib/api/purchase-orders";
import { formatCurrency, formatDate } from "@/lib/utils";
import { toast } from "sonner";
import type { PurchaseOrder } from "@/types/models";

export default function PODetailPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();
    const [po, setPO] = useState<PurchaseOrder | null>(null);
    const [loading, setLoading] = useState(true);
    const [showAckDialog, setShowAckDialog] = useState(false);
    const [deliveryDate, setDeliveryDate] = useState("");
    const [acknowledging, setAcknowledging] = useState(false);

    useEffect(() => {
        poService.get(id).then(setPO).catch(() => toast.error("Failed to load PO")).finally(() => setLoading(false));
    }, [id]);

    const handleAcknowledge = async () => {
        if (!deliveryDate) {
            toast.error("Please select an expected delivery date");
            return;
        }
        setAcknowledging(true);
        try {
            const updated = await poService.acknowledge(id, deliveryDate);
            setPO(updated);
            setShowAckDialog(false);
            toast.success("Purchase Order acknowledged");
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || "Failed to acknowledge");
        } finally {
            setAcknowledging(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" />
            </div>
        );
    }

    if (!po) {
        return (
            <div className="text-center py-20">
                <p className="text-muted-foreground">Purchase Order not found</p>
                <Button variant="outline" className="mt-4" onClick={() => router.push("/purchase-orders")}>
                    <ArrowLeft className="h-4 w-4 mr-2" /> Back to list
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => router.push("/purchase-orders")}>
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold">{po.po_number}</h1>
                        <p className="text-muted-foreground">Purchase Order Details</p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <StatusBadge status={po.status} />
                    {po.status === "ISSUED" && (
                        <Button onClick={() => setShowAckDialog(true)}>
                            <Check className="h-4 w-4 mr-2" /> Acknowledge
                        </Button>
                    )}
                </div>
            </div>

            {/* PO Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="p-5">
                    <h3 className="font-semibold mb-4">Order Details</h3>
                    <div className="space-y-3">
                        <InfoRow label="PO Number" value={po.po_number} />
                        <InfoRow label="Status" value={<StatusBadge status={po.status} />} />
                        <InfoRow label="Total Amount" value={formatCurrency(po.total_cents, po.currency)} />
                        <InfoRow label="Currency" value={po.currency} />
                        <InfoRow label="Issued Date" value={formatDate(po.issued_at)} />
                        <InfoRow label="Expected Delivery" value={formatDate(po.expected_delivery_date)} />
                    </div>
                </Card>

                <Card className="p-5">
                    <h3 className="font-semibold mb-4">Additional Info</h3>
                    <div className="space-y-3">
                        <InfoRow label="Created" value={formatDate(po.created_at)} />
                        <InfoRow label="Last Updated" value={formatDate(po.updated_at)} />
                        {po.terms_and_conditions && (
                            <div>
                                <p className="text-xs text-muted-foreground">Terms & Conditions</p>
                                <p className="text-sm mt-1">{po.terms_and_conditions}</p>
                            </div>
                        )}
                    </div>
                </Card>
            </div>

            {/* Line Items */}
            <Card className="p-5">
                <h3 className="font-semibold mb-4">Line Items</h3>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead>
                            <tr className="border-b bg-muted/50">
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">#</th>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">Description</th>
                                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-muted-foreground">Qty</th>
                                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-muted-foreground">Unit Price</th>
                                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-muted-foreground">Line Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {po.line_items?.map((item, i) => (
                                <tr key={item.id} className="border-b">
                                    <td className="px-4 py-3 text-sm">{item.line_number || i + 1}</td>
                                    <td className="px-4 py-3 text-sm">{item.description}</td>
                                    <td className="px-4 py-3 text-sm text-right">{item.quantity}</td>
                                    <td className="px-4 py-3 text-sm text-right">{formatCurrency(item.unit_price_cents, po.currency)}</td>
                                    <td className="px-4 py-3 text-sm text-right font-medium">
                                        {formatCurrency(item.quantity * item.unit_price_cents, po.currency)}
                                    </td>
                                </tr>
                            ))}
                            <tr className="font-semibold">
                                <td colSpan={4} className="px-4 py-3 text-sm text-right">Total</td>
                                <td className="px-4 py-3 text-sm text-right">{formatCurrency(po.total_cents, po.currency)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </Card>

            {/* Acknowledge Dialog */}
            <Dialog open={showAckDialog} onOpenChange={setShowAckDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Acknowledge Purchase Order</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <p className="text-sm text-muted-foreground">
                            Confirm that you have received {po.po_number} and set your expected delivery date.
                        </p>
                        <div className="space-y-2">
                            <Label htmlFor="delivery-date">Expected Delivery Date</Label>
                            <Input
                                id="delivery-date"
                                type="date"
                                value={deliveryDate}
                                onChange={(e) => setDeliveryDate(e.target.value)}
                                min={new Date().toISOString().split("T")[0]}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowAckDialog(false)}>Cancel</Button>
                        <Button onClick={handleAcknowledge} disabled={acknowledging}>
                            {acknowledging ? (
                                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                            ) : (
                                <>
                                    <Calendar className="h-4 w-4 mr-2" /> Confirm
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
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
