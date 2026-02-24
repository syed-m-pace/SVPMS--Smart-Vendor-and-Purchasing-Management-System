"use client";

import { useEffect, useState, useMemo } from "react";
import { Upload } from "lucide-react";
import { DataTable } from "@/components/shared/DataTable";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { receiptService } from "@/lib/api/services";
import { poService } from "@/lib/api/purchase-orders";
import { api } from "@/lib/api/client";
import { formatDate } from "@/lib/utils";
import type { Receipt, PurchaseOrder } from "@/types/models";
import { toast } from "sonner";

export default function ReceiptsPage() {
    const [receipts, setReceipts] = useState<Receipt[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    const [uploadOpen, setUploadOpen] = useState(false);
    const [issuedPOs, setIssuedPOs] = useState<PurchaseOrder[]>([]);
    const [uploading, setUploading] = useState(false);

    const [formPoId, setFormPoId] = useState("");
    const [formNotes, setFormNotes] = useState("");
    const [formFile, setFormFile] = useState<File | null>(null);
    const [lineItemQuantities, setLineItemQuantities] = useState<Record<string, string>>({});

    useEffect(() => {
        loadReceipts();
    }, [page]);

    const loadReceipts = () => {
        setLoading(true);
        receiptService.list({ page }).then((r) => {
            setReceipts(r.data);
            setTotalPages(r.pagination.total_pages);
        }).catch(() => { }).finally(() => setLoading(false));
    };

    async function openUploadDialog() {
        try {
            const [issuedRes, ackRes, partialRes] = await Promise.all([
                poService.list({ status: "ISSUED", limit: 25 }),
                poService.list({ status: "ACKNOWLEDGED", limit: 25 }),
                poService.list({ status: "PARTIALLY_RECEIVED", limit: 25 }),
            ]);
            setIssuedPOs([...issuedRes.data, ...ackRes.data, ...partialRes.data]);
        } catch {
            toast.error("Failed to load purchase orders");
        }
        setUploadOpen(true);
    }

    const selectedPO = useMemo(() => {
        return issuedPOs.find(po => po.id === formPoId);
    }, [formPoId, issuedPOs]);

    const handleQuantityChange = (lineItemId: string, value: string) => {
        setLineItemQuantities(prev => ({
            ...prev,
            [lineItemId]: value
        }));
    };

    async function handleUploadSubmit() {
        if (!formPoId) {
            toast.error("Please select a Purchase Order");
            return;
        }

        const lineItems = [];
        if (selectedPO?.line_items) {
            for (const li of selectedPO.line_items) {
                const qtyStr = lineItemQuantities[li.id];
                if (qtyStr) {
                    const qty = parseInt(qtyStr, 10);
                    if (qty > 0) {
                        lineItems.push({
                            po_line_item_id: li.id,
                            quantity_received: qty,
                            condition: "GOOD"
                        });
                    }
                }
            }
        }

        if (lineItems.length === 0) {
            toast.error("Please enter received quantity for at least one line item");
            return;
        }

        setUploading(true);
        try {
            let documentKey: string | undefined;
            if (formFile) {
                const fd = new FormData();
                fd.append("file", formFile);
                const { data } = await api.post<{ file_key: string }>("/files/upload", fd);
                documentKey = data.file_key;
            }

            await receiptService.create({
                po_id: formPoId,
                notes: formNotes || undefined,
                document_key: documentKey,
                line_items: lineItems,
            });

            toast.success("Receipt uploaded successfully");
            setUploadOpen(false);
            setFormPoId("");
            setFormNotes("");
            setFormFile(null);
            setLineItemQuantities({});
            loadReceipts();
        } catch (e: any) {
            toast.error(e?.response?.data?.detail || "Failed to upload receipt");
        } finally {
            setUploading(false);
        }
    }

    const columns = [
        { header: "Receipt #", cell: (r: Receipt) => <span className="font-mono font-medium">{r.receipt_number}</span> },
        { header: "PO ID", cell: (r: Receipt) => <span className="font-mono text-xs">{r.po_id.slice(0, 8)}…</span> },
        { header: "Received", cell: (r: Receipt) => formatDate(r.received_at || r.created_at) },
        { header: "Notes", cell: (r: Receipt) => <span className="text-muted-foreground">{r.notes || "—"}</span> },
    ];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Receipts</h1>
                    <p className="text-muted-foreground mt-1">Goods receipt tracking</p>
                </div>
                <Button onClick={openUploadDialog}>
                    <Upload className="mr-2 h-4 w-4" />
                    Upload Receipt
                </Button>
            </div>
            <DataTable columns={columns} data={receipts} loading={loading} page={page} totalPages={totalPages} onPageChange={setPage} />

            <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
                <DialogContent className="sm:max-w-md max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>Upload Receipt</DialogTitle>
                        <DialogDescription>Record goods received against a Purchase Order.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-1">
                            <Label>Purchase Order *</Label>
                            <Select value={formPoId} onValueChange={setFormPoId}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select a PO" />
                                </SelectTrigger>
                                <SelectContent>
                                    {issuedPOs.map((po) => (
                                        <SelectItem key={po.id} value={po.id}>
                                            {po.po_number} — {po.vendor_name || po.vendor_id}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {selectedPO && selectedPO.line_items && selectedPO.line_items.length > 0 && (
                            <div className="space-y-3 mt-4 border rounded-md p-3">
                                <Label className="text-sm font-semibold">Line Items Received</Label>
                                {selectedPO.line_items.map(li => {
                                    const remaining = li.quantity - (li.received_quantity || 0);
                                    if (remaining <= 0) return null;

                                    return (
                                        <div key={li.id} className="flex flex-col space-y-1 pb-2 border-b last:border-0 last:pb-0">
                                            <div className="text-sm font-medium">{li.description}</div>
                                            <div className="flex items-center justify-between text-xs text-muted-foreground">
                                                <span>Ordered: {li.quantity} | Remaining: {remaining}</span>
                                                <div className="flex items-center space-x-2">
                                                    <span>Qty:</span>
                                                    <Input
                                                        type="number"
                                                        min="0"
                                                        max={remaining}
                                                        className="h-7 w-20 text-xs"
                                                        value={lineItemQuantities[li.id] || ""}
                                                        onChange={(e) => handleQuantityChange(li.id, e.target.value)}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        <div className="space-y-1 mt-4">
                            <Label>Notes</Label>
                            <Input value={formNotes} onChange={(e) => setFormNotes(e.target.value)} placeholder="Condition notes or delivery info" />
                        </div>
                        <div className="space-y-1 mt-2">
                            <Label>Document (Delivery Challan / Receipt)</Label>
                            <Input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => setFormFile(e.target.files?.[0] ?? null)} />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setUploadOpen(false)} disabled={uploading}>Cancel</Button>
                        <Button onClick={handleUploadSubmit} disabled={uploading}>
                            {uploading ? "Uploading..." : "Record Receipt"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
