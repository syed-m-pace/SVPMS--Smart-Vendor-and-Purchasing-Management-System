"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Loader2 } from "lucide-react";
import { vendorService } from "@/lib/api/vendors";
import { toast } from "sonner";

const vendorSchema = z.object({
    legal_name: z.string().min(2, "Min 2 characters").max(200),
    tax_id: z.string().regex(/^[A-Z0-9]{10,15}$/, "10-15 uppercase alphanumeric characters"),
    email: z.string().email("Valid email required"),
    phone: z.string().regex(/^\+?[1-9]\d{1,14}$/, "Valid phone number").optional().or(z.literal("")),
    bank_name: z.string().max(200).optional().or(z.literal("")),
    ifsc_code: z.string().regex(/^[A-Z]{4}0[A-Z0-9]{6}$/, "Valid IFSC code").optional().or(z.literal("")),
});

type VendorForm = z.infer<typeof vendorSchema>;

export default function NewVendorPage() {
    const router = useRouter();
    const [submitting, setSubmitting] = useState(false);

    const { register, handleSubmit, formState: { errors } } = useForm<VendorForm>({
        resolver: zodResolver(vendorSchema),
    });

    async function onSubmit(data: VendorForm) {
        setSubmitting(true);
        try {
            // Clean optional empty strings
            const payload: any = { ...data };
            if (!payload.phone) delete payload.phone;
            if (!payload.bank_name) delete payload.bank_name;
            if (!payload.ifsc_code) delete payload.ifsc_code;

            const vendor = await vendorService.create(payload);
            toast.success(`Vendor "${vendor.legal_name}" created`);
            router.push(`/vendors/${vendor.id}`);
        } catch (e: any) {
            toast.error(e.response?.data?.detail || "Failed to create vendor");
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Add Vendor</h1>
                    <p className="text-muted-foreground mt-1">Register a new vendor in the system</p>
                </div>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <Card>
                    <CardHeader><CardTitle className="text-lg">Vendor Information</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Legal Name *</label>
                                <Input {...register("legal_name")} placeholder="Acme Corp Pvt Ltd" />
                                {errors.legal_name && <p className="text-sm text-destructive mt-1">{errors.legal_name.message}</p>}
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2">Tax ID (GSTIN/PAN) *</label>
                                <Input {...register("tax_id")} placeholder="22AAAAA0000A1Z5" className="uppercase" />
                                {errors.tax_id && <p className="text-sm text-destructive mt-1">{errors.tax_id.message}</p>}
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Email *</label>
                                <Input type="email" {...register("email")} placeholder="vendor@example.com" />
                                {errors.email && <p className="text-sm text-destructive mt-1">{errors.email.message}</p>}
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2">Phone</label>
                                <Input {...register("phone")} placeholder="+919876543210" />
                                {errors.phone && <p className="text-sm text-destructive mt-1">{errors.phone.message}</p>}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader><CardTitle className="text-lg">Bank Details (Optional)</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Bank Name</label>
                                <Input {...register("bank_name")} placeholder="State Bank of India" />
                                {errors.bank_name && <p className="text-sm text-destructive mt-1">{errors.bank_name.message}</p>}
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2">IFSC Code</label>
                                <Input {...register("ifsc_code")} placeholder="SBIN0001234" className="uppercase" />
                                {errors.ifsc_code && <p className="text-sm text-destructive mt-1">{errors.ifsc_code.message}</p>}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <div className="flex justify-end gap-3">
                    <Button type="button" variant="outline" onClick={() => router.back()} disabled={submitting}>Cancel</Button>
                    <Button type="submit" disabled={submitting}>
                        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Create Vendor
                    </Button>
                </div>
            </form>
        </div>
    );
}
