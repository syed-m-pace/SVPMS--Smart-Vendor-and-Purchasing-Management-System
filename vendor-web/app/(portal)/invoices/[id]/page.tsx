"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ExternalLink, AlertTriangle, CheckCircle, Clock, Banknote } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { invoiceService } from "@/lib/api/invoices";
import { fileService } from "@/lib/api/files";
import { formatCurrency, formatDate } from "@/lib/utils";
import { toast } from "sonner";
import type { Invoice } from "@/types/models";

function StatusBanner({ status }: { status: string }) {
    switch (status) {
        case "UPLOADED":
            return (
                <div className="flex items-center gap-3 p-4 rounded-lg bg-accent/10 border border-accent/20">
                    <Clock className="h-5 w-5 text-accent" />
                    <div>
                        <p className="text-sm font-medium text-accent">Processing</p>
                        <p className="text-xs text-muted-foreground">OCR processing in progress. Results will appear shortly.</p>
                    </div>
                </div>
            );
        case "MATCHED":
            return (
                <div className="flex items-center gap-3 p-4 rounded-lg bg-success/10 border border-success/20">
                    <CheckCircle className="h-5 w-5 text-success" />
                    <div>
                        <p className="text-sm font-medium text-success">3-Way Match Passed</p>
                        <p className="text-xs text-muted-foreground">Invoice matches PO and receipt. Awaiting payment approval.</p>
                    </div>
                </div>
            );
        case "EXCEPTION":
        case "DISPUTED":
            return (
                <div className="flex items-center gap-3 p-4 rounded-lg bg-warning/10 border border-warning/20">
                    <AlertTriangle className="h-5 w-5 text-warning" />
                    <div>
                        <p className="text-sm font-medium text-warning">
                            {status === "EXCEPTION" ? "Match Exception Detected" : "Invoice Disputed"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                            {status === "EXCEPTION"
                                ? "There is a discrepancy between invoice, PO, and receipt. You can dispute this if you believe it is incorrect."
                                : "Your dispute has been submitted and is under review."}
                        </p>
                    </div>
                </div>
            );
        case "APPROVED":
            return (
                <div className="flex items-center gap-3 p-4 rounded-lg bg-success/10 border border-success/20">
                    <CheckCircle className="h-5 w-5 text-success" />
                    <div>
                        <p className="text-sm font-medium text-success">Approved for Payment</p>
                        <p className="text-xs text-muted-foreground">Invoice has been approved. Payment will be processed shortly.</p>
                    </div>
                </div>
            );
        case "PAID":
            return (
                <div className="flex items-center gap-3 p-4 rounded-lg bg-[hsl(175,70%,40%)]/10 border border-[hsl(175,70%,40%)]/20">
                    <Banknote className="h-5 w-5 text-[hsl(175,70%,40%)]" />
                    <div>
                        <p className="text-sm font-medium text-[hsl(175,70%,40%)]">Payment Complete</p>
                        <p className="text-xs text-muted-foreground">This invoice has been paid.</p>
                    </div>
                </div>
            );
        default:
            return null;
    }
}

export default function InvoiceDetailPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();
    const [invoice, setInvoice] = useState<Invoice | null>(null);
    const [loading, setLoading] = useState(true);
    const [showDisputeDialog, setShowDisputeDialog] = useState(false);
    const [disputeReason, setDisputeReason] = useState("");
    const [disputing, setDisputing] = useState(false);

    useEffect(() => {
        invoiceService.get(id).then(setInvoice).catch(() => toast.error("Failed to load invoice")).finally(() => setLoading(false));
    }, [id]);

    const handleViewDocument = async () => {
        if (!invoice?.document_url) return;
        try {
            const key = invoice.document_url;
            const { url } = await fileService.getPresignedUrl(key);
            window.open(url, "_blank");
        } catch {
            toast.error("Failed to load document");
        }
    };

    const handleDispute = async () => {
        setDisputing(true);
        try {
            const updated = await invoiceService.dispute(id, disputeReason || undefined);
            setInvoice(updated);
            setShowDisputeDialog(false);
            setDisputeReason("");
            toast.success("Invoice disputed successfully");
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || "Failed to dispute invoice");
        } finally {
            setDisputing(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" />
            </div>
        );
    }

    if (!invoice) {
        return (
            <div className="text-center py-20">
                <p className="text-muted-foreground">Invoice not found</p>
                <Button variant="outline" className="mt-4" onClick={() => router.push("/invoices")}>
                    <ArrowLeft className="h-4 w-4 mr-2" /> Back
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => router.push("/invoices")}>
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold">{invoice.invoice_number}</h1>
                        <p className="text-muted-foreground">Invoice Details</p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <StatusBadge status={invoice.status} />
                    {invoice.document_url && (
                        <Button variant="outline" onClick={handleViewDocument}>
                            <ExternalLink className="h-4 w-4 mr-2" /> View Document
                        </Button>
                    )}
                    {(invoice.status === "EXCEPTION") && (
                        <Button variant="destructive" onClick={() => setShowDisputeDialog(true)}>
                            Dispute
                        </Button>
                    )}
                </div>
            </div>

            {/* Status Banner */}
            <StatusBanner status={invoice.status} />

            {/* Invoice Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="p-5">
                    <h3 className="font-semibold mb-4">Invoice Details</h3>
                    <div className="space-y-3">
                        <InfoRow label="Invoice Number" value={invoice.invoice_number} />
                        <InfoRow label="Status" value={<StatusBadge status={invoice.status} />} />
                        <InfoRow label="Total Amount" value={formatCurrency(invoice.total_cents, invoice.currency)} />
                        <InfoRow label="Currency" value={invoice.currency} />
                        <InfoRow label="Invoice Date" value={formatDate(invoice.invoice_date)} />
                        <InfoRow label="PO Number" value={invoice.po_number || "—"} />
                    </div>
                </Card>

                <Card className="p-5">
                    <h3 className="font-semibold mb-4">Processing Status</h3>
                    <div className="space-y-3">
                        <InfoRow label="OCR Status" value={invoice.ocr_status ? <StatusBadge status={invoice.ocr_status} /> : "—"} />
                        <InfoRow label="Match Status" value={invoice.match_status ? <StatusBadge status={invoice.match_status} /> : "—"} />
                        <InfoRow label="Created" value={formatDate(invoice.created_at)} />
                        <InfoRow label="Last Updated" value={formatDate(invoice.updated_at)} />
                        {invoice.approved_payment_at && (
                            <InfoRow label="Payment Approved" value={formatDate(invoice.approved_payment_at)} />
                        )}
                        {invoice.paid_at && (
                            <InfoRow label="Paid At" value={formatDate(invoice.paid_at)} />
                        )}
                    </div>
                </Card>
            </div>

            {/* Line Items */}
            {invoice.line_items && invoice.line_items.length > 0 && (
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
                                    <th className="px-4 py-3 text-right text-xs font-medium uppercase text-muted-foreground">Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {invoice.line_items.map((item, i) => (
                                    <tr key={item.id} className="border-b">
                                        <td className="px-4 py-3 text-sm">{item.line_number || i + 1}</td>
                                        <td className="px-4 py-3 text-sm">{item.description}</td>
                                        <td className="px-4 py-3 text-sm text-right">{item.quantity}</td>
                                        <td className="px-4 py-3 text-sm text-right">{formatCurrency(item.unit_price_cents, invoice.currency)}</td>
                                        <td className="px-4 py-3 text-sm text-right font-medium">
                                            {formatCurrency(item.quantity * item.unit_price_cents, invoice.currency)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}

            {/* Dispute Dialog */}
            <Dialog open={showDisputeDialog} onOpenChange={setShowDisputeDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Dispute Invoice</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <p className="text-sm text-muted-foreground">
                            If you believe the match exception is incorrect, describe the issue below.
                        </p>
                        <div className="space-y-2">
                            <Label htmlFor="dispute-reason">Reason (optional)</Label>
                            <Textarea
                                id="dispute-reason"
                                placeholder="Describe why you are disputing this invoice..."
                                rows={4}
                                value={disputeReason}
                                onChange={(e) => setDisputeReason(e.target.value)}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowDisputeDialog(false)}>Cancel</Button>
                        <Button variant="destructive" onClick={handleDispute} disabled={disputing}>
                            {disputing ? (
                                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                            ) : (
                                "Submit Dispute"
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
