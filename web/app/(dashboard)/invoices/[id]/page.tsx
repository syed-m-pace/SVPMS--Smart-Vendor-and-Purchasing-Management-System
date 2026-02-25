"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ExternalLink, Loader2 } from "lucide-react";
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
    const [approvePaymentOpen, setApprovePaymentOpen] = useState(false);
    const [approvingPayment, setApprovingPayment] = useState(false);
    const [markPaidOpen, setMarkPaidOpen] = useState(false);
    const [markingPaid, setMarkingPaid] = useState(false);

    useEffect(() => {
        invoiceService.get(params.id as string).then(setInv).catch(() => toast.error("Failed")).finally(() => setLoading(false));
    }, [params.id]);

    async function handleApprovePayment() {
        if (!inv) return;
        setApprovingPayment(true);
        try {
            const updated = await invoiceService.approvePayment(inv.id, "Manual override approval for stuck OCR");
            setInv(updated);
            toast.success("Invoice approved for payment");
        } catch {
            toast.error("Failed to approve payment");
        } finally {
            setApprovingPayment(false);
            setApprovePaymentOpen(false);
        }
    }

    async function handleRaiseException() {
        if (!inv) return;
        const reason = window.prompt("Exception / Dispute Reason (min 5 chars):");
        if (!reason || reason.length < 5) return;

        try {
            const updated = await invoiceService.dispute(inv.id, reason);
            setInv(updated);
            toast.success("Exception raised successfully");
        } catch {
            toast.error("Failed to raise exception");
        }
    }

    async function handleMarkPaid() {
        if (!inv) return;
        setMarkingPaid(true);
        try {
            const updated = await invoiceService.pay(inv.id);
            setInv(updated);
            toast.success("Invoice marked as paid");
        } catch {
            toast.error("Failed to mark invoice as paid");
        } finally {
            setMarkingPaid(false);
            setMarkPaidOpen(false);
        }
    }

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
                    {inv.vendor_name && (
                        <p className="text-sm text-muted-foreground mt-1">Vendor: <span className="text-foreground font-medium">{inv.vendor_name}</span></p>
                    )}
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
                <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">OCR Status</p><div className="mt-1">{inv.ocr_status ? <StatusBadge status={inv.ocr_status} /> : <span className="text-lg font-medium text-muted-foreground">N/A</span>}</div></CardContent></Card>
                {inv.approved_payment_at && (
                    <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Approved for Payment</p><p className="text-lg font-medium">{formatDate(inv.approved_payment_at)}</p></CardContent></Card>
                )}
                {inv.paid_at && (
                    <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Paid At</p><p className="text-lg font-medium">{formatDate(inv.paid_at)}</p></CardContent></Card>
                )}
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
                <CardHeader><CardTitle className="text-lg">Next Steps</CardTitle></CardHeader>
                <CardContent className="text-sm space-y-3">
                    {inv.status === "UPLOADED" && (
                        <div className="space-y-4">
                            <p className="text-muted-foreground">OCR processing in progress. The invoice will be automatically matched against the purchase order once extraction completes.</p>
                            <div className="bg-muted/50 p-4 rounded-lg border space-y-3">
                                <p className="text-sm font-medium">Manual Override Controls</p>
                                <p className="text-xs text-muted-foreground">If OCR is failing or stuck, you can manually push this invoice forward or raise an exception back to the vendor.</p>
                                <div className="flex gap-3 flex-wrap pt-2">
                                    <Button size="sm" onClick={() => setApprovePaymentOpen(true)}>
                                        Manually Approve Payment
                                    </Button>
                                    <Button size="sm" variant="outline" className="text-destructive hover:bg-destructive/10 hover:text-destructive" onClick={handleRaiseException}>
                                        Raise Exception
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}
                    {inv.status === "MATCHED" && (
                        <div className="space-y-2">
                            <p className="text-green-600 font-medium">3-way match passed. This invoice is ready for payment approval.</p>
                            <Button size="sm" onClick={() => setApprovePaymentOpen(true)}>Approve for Payment</Button>
                        </div>
                    )}
                    {inv.status === "APPROVED" && (
                        <div className="space-y-2">
                            <p className="text-blue-600 font-medium">Invoice approved for payment. Ready to mark as paid.</p>
                            <Button size="sm" variant="outline" onClick={() => setMarkPaidOpen(true)}>Mark as Paid</Button>
                        </div>
                    )}
                    {(inv.status === "EXCEPTION" || inv.status === "DISPUTED") && (
                        <div className="space-y-2">
                            <p className="text-amber-600 font-medium">A match exception was detected. Review the exceptions above and take action.</p>
                            <div className="flex gap-2 flex-wrap">
                                <Button variant="outline" size="sm" onClick={async () => {
                                    const reason = window.prompt("Override reason (min 10 chars):");
                                    if (!reason || reason.length < 10) return;
                                    try {
                                        await api.post(`/invoices/${inv.id}/override`, { reason });
                                        const updated = await invoiceService.get(inv.id);
                                        setInv(updated);
                                        toast.success("Invoice overridden");
                                    } catch { toast.error("Override failed"); }
                                }}>Override Match</Button>
                            </div>
                        </div>
                    )}
                    {inv.status === "PAID" && (
                        <p className="text-muted-foreground">This invoice has been paid.</p>
                    )}
                </CardContent>
            </Card>

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

            <AlertDialog open={approvePaymentOpen} onOpenChange={setApprovePaymentOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Approve for Payment</AlertDialogTitle>
                        <AlertDialogDescription>
                            Approve invoice <strong>{inv.invoice_number}</strong> for payment? This will notify the vendor.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={approvingPayment}>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={handleApprovePayment} disabled={approvingPayment}>
                            {approvingPayment && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Approve
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <AlertDialog open={markPaidOpen} onOpenChange={setMarkPaidOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Mark as Paid</AlertDialogTitle>
                        <AlertDialogDescription>
                            Confirm payment for invoice <strong>{inv.invoice_number}</strong>? This will notify the vendor.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={markingPaid}>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={handleMarkPaid} disabled={markingPaid}>
                            {markingPaid && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Mark as Paid
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
