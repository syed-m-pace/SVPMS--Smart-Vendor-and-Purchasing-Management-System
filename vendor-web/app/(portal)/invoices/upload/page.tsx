"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { ArrowLeft, Upload, FileText, X } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { poService } from "@/lib/api/purchase-orders";
import { invoiceService } from "@/lib/api/invoices";
import { fileService } from "@/lib/api/files";
import { invoiceUploadSchema, type InvoiceUploadFormData } from "@/lib/validations/invoice-upload";
import { toast } from "sonner";
import type { PurchaseOrder } from "@/types/models";

export default function InvoiceUploadPage() {
    const router = useRouter();
    const [pos, setPOs] = useState<PurchaseOrder[]>([]);
    const [file, setFile] = useState<File | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const {
        register,
        handleSubmit,
        setValue,
        formState: { errors },
    } = useForm<InvoiceUploadFormData>({
        resolver: zodResolver(invoiceUploadSchema),
    });

    useEffect(() => {
        poService.list({ per_page: 100 }).then((res) => setPOs(res.data)).catch(() => { });
    }, []);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles.length > 0) setFile(acceptedFiles[0]);
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            "application/pdf": [".pdf"],
            "image/jpeg": [".jpg", ".jpeg"],
            "image/png": [".png"],
        },
        maxFiles: 1,
        maxSize: 10 * 1024 * 1024, // 10MB
    });

    const onSubmit = async (formData: InvoiceUploadFormData) => {
        if (!file) {
            toast.error("Please attach an invoice document");
            return;
        }
        setSubmitting(true);
        try {
            // Upload file first
            const fileResult = await fileService.upload(file);

            // Create invoice
            await invoiceService.create({
                po_id: formData.po_id,
                invoice_number: formData.invoice_number,
                invoice_date: formData.invoice_date,
                total_cents: Math.round(formData.total_amount * 100),
                document_key: fileResult.file_key,
            });

            toast.success("Invoice uploaded successfully");
            router.push("/invoices");
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || "Failed to upload invoice");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.push("/invoices")}>
                    <ArrowLeft className="h-5 w-5" />
                </Button>
                <div>
                    <h1 className="text-2xl font-bold">Upload Invoice</h1>
                    <p className="text-muted-foreground">Submit a new invoice against a purchase order</p>
                </div>
            </div>

            <Card className="p-5">
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                    {/* PO Selector */}
                    <div className="space-y-2">
                        <Label>Purchase Order</Label>
                        <Select onValueChange={(val) => setValue("po_id", val)}>
                            <SelectTrigger>
                                <SelectValue placeholder="Select a PO" />
                            </SelectTrigger>
                            <SelectContent>
                                {pos.map((po) => (
                                    <SelectItem key={po.id} value={po.id}>
                                        {po.po_number} — {po.currency} {(po.total_cents / 100).toLocaleString()}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {errors.po_id && <p className="text-xs text-destructive">{errors.po_id.message}</p>}
                    </div>

                    {/* Invoice Number */}
                    <div className="space-y-2">
                        <Label htmlFor="invoice_number">Invoice Number</Label>
                        <Input
                            id="invoice_number"
                            placeholder="e.g., INV-2026-001"
                            {...register("invoice_number")}
                        />
                        {errors.invoice_number && <p className="text-xs text-destructive">{errors.invoice_number.message}</p>}
                    </div>

                    {/* Invoice Date */}
                    <div className="space-y-2">
                        <Label htmlFor="invoice_date">Invoice Date</Label>
                        <Input
                            id="invoice_date"
                            type="date"
                            {...register("invoice_date")}
                        />
                        {errors.invoice_date && <p className="text-xs text-destructive">{errors.invoice_date.message}</p>}
                    </div>

                    {/* Total Amount */}
                    <div className="space-y-2">
                        <Label htmlFor="total_amount">Total Amount (INR)</Label>
                        <Input
                            id="total_amount"
                            type="number"
                            step="0.01"
                            placeholder="e.g., 5000.00"
                            {...register("total_amount", { valueAsNumber: true })}
                        />
                        {errors.total_amount && <p className="text-xs text-destructive">{errors.total_amount.message}</p>}
                    </div>

                    {/* File Upload */}
                    <div className="space-y-2">
                        <Label>Invoice Document</Label>
                        {file ? (
                            <div className="flex items-center gap-3 p-3 rounded-lg border bg-muted/50">
                                <FileText className="h-5 w-5 text-accent" />
                                <div className="flex-1 truncate">
                                    <p className="text-sm font-medium truncate">{file.name}</p>
                                    <p className="text-xs text-muted-foreground">
                                        {(file.size / 1024).toFixed(1)} KB
                                    </p>
                                </div>
                                <button type="button" onClick={() => setFile(null)} className="text-muted-foreground hover:text-foreground">
                                    <X className="h-4 w-4" />
                                </button>
                            </div>
                        ) : (
                            <div
                                {...getRootProps()}
                                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                                    isDragActive ? "border-accent bg-accent/5" : "border-border hover:border-accent/50"
                                }`}
                            >
                                <input {...getInputProps()} />
                                <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                                <p className="text-sm text-muted-foreground">
                                    Drag & drop your invoice here, or click to browse
                                </p>
                                <p className="text-xs text-muted-foreground mt-1">
                                    PDF, JPG, PNG — Max 10 MB
                                </p>
                            </div>
                        )}
                    </div>

                    <div className="flex gap-3 pt-2">
                        <Button type="button" variant="outline" onClick={() => router.back()} className="flex-1">
                            Cancel
                        </Button>
                        <Button type="submit" disabled={submitting} className="flex-1">
                            {submitting ? (
                                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                            ) : (
                                <>
                                    <Upload className="h-4 w-4 mr-2" /> Upload Invoice
                                </>
                            )}
                        </Button>
                    </div>
                </form>
            </Card>
        </div>
    );
}
