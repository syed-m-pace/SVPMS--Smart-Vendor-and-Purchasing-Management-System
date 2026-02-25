"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { poService } from "@/lib/api/purchase-orders";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { PurchaseOrder } from "@/types/models";
import { toast } from "sonner";
import { isAxiosError } from "axios";

export default function PODetailPage() {
    const params = useParams();
    const router = useRouter();
    const [po, setPo] = useState<PurchaseOrder | null>(null);
    const [loading, setLoading] = useState(true);
    const [canceling, setCanceling] = useState(false);
    const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
    const [cancelReason, setCancelReason] = useState("");

    const getErrorMessage = (error: unknown, fallback: string) => {
        if (isAxiosError(error)) {
            const detail = error.response?.data?.detail;
            if (typeof detail === "string") return detail;
        }
        return fallback;
    };

    useEffect(() => {
        poService.get(params.id as string).then(setPo).catch(() => toast.error("Failed")).finally(() => setLoading(false));
    }, [params.id]);

    const handleCancel = async () => {
        if (!po || cancelReason.trim().length < 5) return;
        setCanceling(true);
        try {
            const updated = await poService.cancel(po.id, cancelReason);
            setPo(updated);
            toast.success("Purchase Order cancelled successfully");
            setCancelDialogOpen(false);
        } catch (error) {
            toast.error(getErrorMessage(error, "Failed to cancel PO"));
        } finally {
            setCanceling(false);
        }
    };

    if (loading) return <div className="flex justify-center py-20"><div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" /></div>;
    if (!po) return <p>PO not found</p>;

    return (
        <div className="space-y-6 max-w-4xl">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()}><ArrowLeft className="h-4 w-4" /></Button>
                <div className="flex-1">
                    <div className="flex items-center gap-3"><h1 className="text-2xl font-bold font-mono">{po.po_number}</h1><StatusBadge status={po.status} /></div>
                </div>
                {(po.status === "ISSUED" || po.status === "ACKNOWLEDGED") && (
                    <Button
                        variant="outline"
                        onClick={() => setCancelDialogOpen(true)}
                        disabled={canceling}
                        className="gap-2 border-destructive/50 text-destructive hover:bg-destructive/10"
                    >
                        <XCircle className="h-4 w-4" />
                        Cancel PO
                    </Button>
                )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Vendor</p><p className="text-lg font-medium">{po.vendor_name || po.vendor_id.substring(0, 8)}</p></CardContent></Card>
                <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Total</p><p className="text-2xl font-bold font-mono">{formatCurrency(po.total_cents)}</p></CardContent></Card>
                <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Created</p><p className="text-lg font-medium">{formatDate(po.created_at)}</p></CardContent></Card>
                <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Issued</p><p className="text-lg font-medium">{po.issued_at ? formatDate(po.issued_at) : "Not issued"}</p></CardContent></Card>
            </div>
            <Card>
                <CardHeader><CardTitle className="text-lg">Line Items</CardTitle></CardHeader>
                <CardContent>
                    <table className="w-full text-sm">
                        <thead><tr className="border-b bg-muted/50">
                            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">#</th>
                            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">Description</th>
                            <th className="px-4 py-3 text-right text-xs font-medium uppercase text-muted-foreground">Qty</th>
                            <th className="px-4 py-3 text-right text-xs font-medium uppercase text-muted-foreground">Unit Price</th>
                            <th className="px-4 py-3 text-right text-xs font-medium uppercase text-muted-foreground">Total</th>
                        </tr></thead>
                        <tbody>
                            {po.line_items?.map((li) => (
                                <tr key={li.id} className="border-b">
                                    <td className="px-4 py-3">{li.line_number}</td>
                                    <td className="px-4 py-3">{li.description}</td>
                                    <td className="px-4 py-3 text-right font-mono">{li.quantity}</td>
                                    <td className="px-4 py-3 text-right font-mono">{formatCurrency(li.unit_price_cents)}</td>
                                    <td className="px-4 py-3 text-right font-mono font-medium">{formatCurrency(li.quantity * li.unit_price_cents)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </CardContent>
            </Card>

            <AlertDialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Cancel Purchase Order &quot;{po.po_number}&quot;?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to cancel this PO? Vendors will be notified. This action is irreversible.
                        </AlertDialogDescription>
                    </AlertDialogHeader>

                    <div className="py-2">
                        <Label htmlFor="cancel_reason" className="text-sm font-medium">Cancellation Reason (required)</Label>
                        <Input
                            id="cancel_reason"
                            className="mt-1"
                            placeholder="e.g. Budget revoked"
                            value={cancelReason}
                            onChange={(e) => setCancelReason(e.target.value)}
                        />
                    </div>

                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={canceling}>Keep PO</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(e) => {
                                e.preventDefault();
                                handleCancel();
                            }}
                            disabled={canceling || cancelReason.trim().length < 5}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {canceling && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Cancel PO
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
