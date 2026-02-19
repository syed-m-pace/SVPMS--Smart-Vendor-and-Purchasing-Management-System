"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { invoiceService } from "@/lib/api/invoices";
import { api } from "@/lib/api/client";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Invoice } from "@/types/models";
import { toast } from "sonner";

function readConfidence(ocrData: Record<string, unknown> | null): number | null {
    if (!ocrData) return null;
    const value = ocrData["confidence"];
    return typeof value === "number" ? value : null;
}

export default function InvoiceDetailPage() {
    const params = useParams();
    const router = useRouter();
    const [inv, setInv] = useState<Invoice | null>(null);
    const [loading, setLoading] = useState(true);
    const [openingDocument, setOpeningDocument] = useState(false);

    useEffect(() => {
        invoiceService.get(params.id as string).then(setInv).catch(() => toast.error("Failed")).finally(() => setLoading(false));
    }, [params.id]);

    if (loading) return <div className="flex justify-center py-20"><div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" /></div>;
    if (!inv) return <p>Invoice not found</p>;

    const confidence = readConfidence(inv.ocr_data);
    const ocrInvoiceNumber = typeof inv.ocr_data?.invoice_number === "string" ? inv.ocr_data.invoice_number : null;
    const ocrTotalCents = typeof inv.ocr_data?.total_cents === "number" ? inv.ocr_data.total_cents : null;
    const exceptionPayload = inv.match_exceptions ? JSON.stringify(inv.match_exceptions, null, 2) : null;

    async function openDocument() {
        if (!inv?.document_url) return;
        setOpeningDocument(true);
        try {
            const { data } = await api.get<{ presigned_url: string }>(`/files/${inv.document_url}`);
            window.open(data.presigned_url, "_blank", "noopener,noreferrer");
        } catch {
            toast.error("Failed to open invoice document");
        } finally {
            setOpeningDocument(false);
        }
    }

    return (
        <div className="space-y-6 max-w-4xl">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()}><ArrowLeft className="h-4 w-4" /></Button>
                <div className="flex-1">
                    <div className="flex items-center gap-3"><h1 className="text-2xl font-bold font-mono">{inv.invoice_number}</h1><StatusBadge status={inv.status} />{inv.match_status && <StatusBadge status={inv.match_status} />}</div>
                </div>
                {inv.document_url && (
                    <Button variant="outline" onClick={openDocument} disabled={openingDocument}>
                        <ExternalLink className="mr-2 h-4 w-4" />
                        {openingDocument ? "Opening..." : "View Document"}
                    </Button>
                )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Total</p><p className="text-2xl font-bold font-mono">{formatCurrency(inv.total_cents)}</p></CardContent></Card>
                <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Created</p><p className="text-lg font-medium">{formatDate(inv.created_at)}</p></CardContent></Card>
                <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">OCR Status</p><p className="text-lg font-medium capitalize">{inv.ocr_status || "N/A"}</p></CardContent></Card>
            </div>

            <Card>
                <CardHeader><CardTitle className="text-lg">OCR Extracted Data</CardTitle></CardHeader>
                <CardContent className="space-y-2 text-sm">
                    <p><span className="text-muted-foreground">Confidence:</span> {confidence !== null ? `${(confidence * 100).toFixed(1)}%` : "N/A"}</p>
                    <p><span className="text-muted-foreground">Invoice #:</span> {ocrInvoiceNumber || "N/A"}</p>
                    <p><span className="text-muted-foreground">Extracted Total:</span> {ocrTotalCents !== null ? formatCurrency(ocrTotalCents) : "N/A"}</p>
                </CardContent>
            </Card>

            {exceptionPayload && (
                <Card>
                    <CardHeader><CardTitle className="text-lg">Match Exceptions</CardTitle></CardHeader>
                    <CardContent>
                        <pre className="text-xs overflow-x-auto rounded bg-muted p-3">{exceptionPayload}</pre>
                    </CardContent>
                </Card>
            )}

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
                            {inv.line_items?.map((li) => (
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
