"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, Search } from "lucide-react";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
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
import { invoiceService } from "@/lib/api/invoices";
import { poService } from "@/lib/api/purchase-orders";
import { api } from "@/lib/api/client";
import { formatCurrency, timeAgo } from "@/lib/utils";
import type { Invoice, PurchaseOrder } from "@/types/models";
import { toast } from "sonner";

export default function InvoicesPage() {
    const router = useRouter();
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    const [uploadOpen, setUploadOpen] = useState(false);
    const [issuedPOs, setIssuedPOs] = useState<PurchaseOrder[]>([]);
    const [uploading, setUploading] = useState(false);

    const [formPoId, setFormPoId] = useState("");
    const [formInvoiceNumber, setFormInvoiceNumber] = useState("");
    const [formInvoiceDate, setFormInvoiceDate] = useState("");
    const [formAmount, setFormAmount] = useState("");
    const [formFile, setFormFile] = useState<File | null>(null);
    const [search, setSearch] = useState("");
    const [statusFilter, setStatusFilter] = useState("");

    useEffect(() => {
        invoiceService.list({ page, status: statusFilter || undefined }).then((r) => {
            setInvoices(r.data);
            setTotalPages(r.pagination.total_pages);
        }).catch(() => { }).finally(() => setLoading(false));
    }, [page, statusFilter]);

    const filteredInvoices = search
        ? invoices.filter((inv) =>
            inv.invoice_number?.toLowerCase().includes(search.toLowerCase()) ||
            inv.vendor_name?.toLowerCase().includes(search.toLowerCase())
        )
        : invoices;

    async function openUploadDialog() {
        try {
            const [issuedRes, acknowledgedRes] = await Promise.all([
                poService.list({ status: "ISSUED", limit: 25 }),
                poService.list({ status: "ACKNOWLEDGED", limit: 25 }),
            ]);
            setIssuedPOs([...issuedRes.data, ...acknowledgedRes.data]);
        } catch {
            toast.error("Failed to load purchase orders");
        }
        setUploadOpen(true);
    }

    async function handleUploadSubmit() {
        if (!formPoId || !formInvoiceNumber || !formInvoiceDate || !formAmount) {
            toast.error("Please fill in all required fields");
            return;
        }
        const totalCents = Math.round(parseFloat(formAmount) * 100);
        if (isNaN(totalCents) || totalCents <= 0) {
            toast.error("Invalid amount");
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

            await invoiceService.create({
                po_id: formPoId,
                invoice_number: formInvoiceNumber,
                invoice_date: formInvoiceDate,
                total_cents: totalCents,
                document_key: documentKey,
                line_items: [],
            });

            toast.success("Invoice uploaded successfully");
            setUploadOpen(false);
            setFormPoId("");
            setFormInvoiceNumber("");
            setFormInvoiceDate("");
            setFormAmount("");
            setFormFile(null);

            // Refresh list
            setLoading(true);
            const refreshed = await invoiceService.list({ page });
            setInvoices(refreshed.data);
            setTotalPages(refreshed.pagination.total_pages);
        } catch {
            toast.error("Failed to upload invoice");
        } finally {
            setUploading(false);
            setLoading(false);
        }
    }

    const columns = [
        { header: "Invoice #", cell: (inv: Invoice) => <span className="font-mono font-medium">{inv.invoice_number}</span> },
        { header: "Vendor", cell: (inv: Invoice) => <span>{inv.vendor_name || "—"}</span> },
        { header: "Status", cell: (inv: Invoice) => <StatusBadge status={inv.status} /> },
        { header: "Match", cell: (inv: Invoice) => inv.match_status ? <StatusBadge status={inv.match_status} /> : <span className="text-muted-foreground">—</span> },
        { header: "Amount", cell: (inv: Invoice) => <span className="font-mono">{formatCurrency(inv.total_cents)}</span> },
        { header: "Created", cell: (inv: Invoice) => <span className="text-muted-foreground">{timeAgo(inv.created_at)}</span> },
    ];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Invoices</h1>
                    <p className="text-muted-foreground mt-1">Track and manage invoices</p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input placeholder="Search invoices..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9 w-[200px]" />
                    </div>
                    <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 appearance-none pr-8" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 8px center' }}>
                        <option value="">All Statuses</option>
                        {["UPLOADED", "MATCHED", "EXCEPTION", "DISPUTED", "APPROVED", "PAID"].map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <Button onClick={openUploadDialog}>
                        <Upload className="mr-2 h-4 w-4" />
                        Upload Invoice
                    </Button>
                </div>
            </div>
            <DataTable columns={columns} data={filteredInvoices} loading={loading} page={page} totalPages={totalPages} onPageChange={setPage} onRowClick={(inv) => router.push(`/invoices/${inv.id}`)} />

            <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Upload Invoice</DialogTitle>
                        <DialogDescription>Upload an invoice against an existing purchase order.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
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
                        <div className="space-y-1">
                            <Label>Invoice Number *</Label>
                            <Input value={formInvoiceNumber} onChange={(e) => setFormInvoiceNumber(e.target.value)} placeholder="INV-2026-001" />
                        </div>
                        <div className="space-y-1">
                            <Label>Invoice Date *</Label>
                            <Input type="date" value={formInvoiceDate} onChange={(e) => setFormInvoiceDate(e.target.value)} />
                        </div>
                        <div className="space-y-1">
                            <Label>Amount (₹) *</Label>
                            <Input type="number" min="1" step="0.01" value={formAmount} onChange={(e) => setFormAmount(e.target.value)} placeholder="50000.00" />
                        </div>
                        <div className="space-y-1">
                            <Label>Document (PDF / Image)</Label>
                            <Input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => setFormFile(e.target.files?.[0] ?? null)} />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setUploadOpen(false)} disabled={uploading}>Cancel</Button>
                        <Button onClick={handleUploadSubmit} disabled={uploading}>
                            {uploading ? "Uploading..." : "Upload"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
