"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { prService } from "@/lib/api/purchase-requests";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { PurchaseRequest } from "@/types/models";
import { toast } from "sonner";

export default function PRDetailPage() {
    const params = useParams();
    const router = useRouter();
    const [pr, setPr] = useState<PurchaseRequest | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        prService.get(params.id as string).then(setPr).catch(() => toast.error("Failed")).finally(() => setLoading(false));
    }, [params.id]);

    async function handleSubmit() {
        setSubmitting(true);
        try {
            const updated = await prService.submit(pr!.id);
            setPr(updated);
            toast.success("PR submitted for approval");
        } catch (e: any) { toast.error(e.response?.data?.detail?.error?.message || "Failed to submit"); } finally { setSubmitting(false); }
    }

    if (loading) return <div className="flex justify-center py-20"><div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" /></div>;
    if (!pr) return <p>PR not found</p>;

    return (
        <div className="space-y-6 max-w-4xl">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()}><ArrowLeft className="h-4 w-4" /></Button>
                <div className="flex-1">
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-bold font-mono">{pr.pr_number}</h1>
                        <StatusBadge status={pr.status} />
                    </div>
                    <p className="text-muted-foreground mt-1">{pr.description || "No description"}</p>
                </div>
                {pr.status === "DRAFT" && (
                    <Button onClick={handleSubmit} disabled={submitting}>
                        {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
                        Submit for Approval
                    </Button>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Total Amount</p><p className="text-2xl font-bold font-mono">{formatCurrency(pr.total_cents)}</p></CardContent></Card>
                <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Created</p><p className="text-lg font-medium">{formatDate(pr.created_at)}</p></CardContent></Card>
                <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Submitted</p><p className="text-lg font-medium">{pr.submitted_at ? formatDate(pr.submitted_at) : "Not yet"}</p></CardContent></Card>
            </div>

            <Card>
                <CardHeader><CardTitle className="text-lg">Line Items</CardTitle></CardHeader>
                <CardContent>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead><tr className="border-b bg-muted/50">
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">#</th>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">Description</th>
                                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-muted-foreground">Qty</th>
                                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-muted-foreground">Unit Price</th>
                                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-muted-foreground">Total</th>
                            </tr></thead>
                            <tbody>
                                {pr.line_items?.map((li) => (
                                    <tr key={li.id} className="border-b">
                                        <td className="px-4 py-3">{li.line_number}</td>
                                        <td className="px-4 py-3">{li.description}</td>
                                        <td className="px-4 py-3 text-right font-mono">{li.quantity}</td>
                                        <td className="px-4 py-3 text-right font-mono">{formatCurrency(li.unit_price_cents)}</td>
                                        <td className="px-4 py-3 text-right font-mono font-medium">{formatCurrency(li.quantity * li.unit_price_cents)}</td>
                                    </tr>
                                ))}
                            </tbody>
                            <tfoot><tr className="border-t-2">
                                <td colSpan={4} className="px-4 py-3 text-right font-medium">Total</td>
                                <td className="px-4 py-3 text-right font-mono font-bold text-lg">{formatCurrency(pr.total_cents)}</td>
                            </tr></tfoot>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
