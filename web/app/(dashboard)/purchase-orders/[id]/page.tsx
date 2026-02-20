"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { poService } from "@/lib/api/purchase-orders";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { PurchaseOrder } from "@/types/models";
import { toast } from "sonner";

export default function PODetailPage() {
    const params = useParams();
    const router = useRouter();
    const [po, setPo] = useState<PurchaseOrder | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        poService.get(params.id as string).then(setPo).catch(() => toast.error("Failed")).finally(() => setLoading(false));
    }, [params.id]);

    if (loading) return <div className="flex justify-center py-20"><div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" /></div>;
    if (!po) return <p>PO not found</p>;

    return (
        <div className="space-y-6 max-w-4xl">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()}><ArrowLeft className="h-4 w-4" /></Button>
                <div className="flex-1">
                    <div className="flex items-center gap-3"><h1 className="text-2xl font-bold font-mono">{po.po_number}</h1><StatusBadge status={po.status} /></div>
                </div>
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
        </div>
    );
}
