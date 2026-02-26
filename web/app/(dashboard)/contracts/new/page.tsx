"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { contractService } from "@/lib/api/contracts";
import { vendorService } from "@/lib/api/vendors";
import { toast } from "sonner";
import { isAxiosError } from "axios";
import { useAuthStore } from "@/lib/stores/auth";

const formSchema = z.object({
    vendor_id: z.string().optional(),
    title: z.string().min(3, "Title must be at least 3 characters").max(255),
    description: z.string().optional(),
    value: z.string().optional(),
    start_date: z.string().min(1, "Start date is required"),
    end_date: z.string().min(1, "End date is required"),
    renewal_notice_days: z.string().min(1, "Notice days is required"),
    sla_terms: z.string().optional(),
}).refine(data => new Date(data.start_date) < new Date(data.end_date), {
    message: "End date must be after start date",
    path: ["end_date"]
});

type FormValues = z.infer<typeof formSchema>;

export default function NewContractPage() {
    const router = useRouter();
    const { user } = useAuthStore();
    const [submitting, setSubmitting] = useState(false);

    const {
        register,
        handleSubmit,
        setError,
        formState: { errors }
    } = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            vendor_id: "",
            title: "",
            description: "",
            start_date: "",
            end_date: "",
            renewal_notice_days: "30",
            sla_terms: "",
        },
    });

    const getErrorMessage = (error: unknown, fallback: string) => {
        if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
            return error.response.data.detail;
        }
        return fallback;
    };

    const onSubmit = async (data: FormValues) => {
        setSubmitting(true);
        try {
            if (data.vendor_id && data.vendor_id.trim().length > 0) {
                try {
                    await vendorService.get(data.vendor_id.trim());
                } catch {
                    setError("vendor_id", { message: "Invalid Vendor ID or Vendor not found" });
                    setSubmitting(false);
                    return;
                }
            }

            const payload = {
                vendor_id: data.vendor_id && data.vendor_id.trim() !== "" ? data.vendor_id.trim() : null,
                title: data.title,
                description: data.description,
                start_date: data.start_date,
                end_date: data.end_date,
                renewal_notice_days: parseInt(data.renewal_notice_days, 10),
                sla_terms: data.sla_terms,
                value_cents: data.value ? Math.round(parseFloat(data.value) * 100) : null,
                currency: "INR",
                auto_renew: false,
            };

            const created = await contractService.create(payload);
            toast.success("Contract draft created successfully");
            router.push(`/contracts/${created.id}`);
        } catch (error) {
            toast.error(getErrorMessage(error, "Failed to create contract"));
        } finally {
            setSubmitting(false);
        }
    };

    if (!user || !["admin", "procurement_lead", "procurement", "manager", "finance_head", "cfo"].includes(user.role)) {
        return <div className="p-8 text-center text-destructive">You do not have permission to create contracts.</div>;
    }

    return (
        <div className="max-w-3xl mx-auto space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()}>
                    <ArrowLeft className="h-5 w-5" />
                </Button>
                <div>
                    <h1 className="text-2xl font-bold">New Contract</h1>
                    <p className="text-muted-foreground">Draft a new vendor agreement</p>
                </div>
            </div>

            <div className="bg-card border rounded-xl p-6 shadow-sm">
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <Label htmlFor="vendor_id">Vendor ID (Optional)</Label>
                            <Input id="vendor_id" placeholder="UUID... (leave blank for master contract)" {...register("vendor_id")} />
                            {errors.vendor_id && <p className="text-sm text-destructive">{errors.vendor_id.message}</p>}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="title">Contract Title *</Label>
                            <Input id="title" placeholder="e.g. Master Services Agreement 2026" {...register("title")} />
                            {errors.title && <p className="text-sm text-destructive">{errors.title.message}</p>}
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <Label htmlFor="start_date">Start Date *</Label>
                            <Input id="start_date" type="date" {...register("start_date")} />
                            {errors.start_date && <p className="text-sm text-destructive">{errors.start_date.message}</p>}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="end_date">End Date *</Label>
                            <Input id="end_date" type="date" {...register("end_date")} />
                            {errors.end_date && <p className="text-sm text-destructive">{errors.end_date.message}</p>}
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <Label htmlFor="value">Total Value (Optional, INR)</Label>
                            <Input id="value" type="number" step="0.01" min="0" placeholder="Optional value..." {...register("value")} />
                            {errors.value && <p className="text-sm text-destructive">{errors.value.message}</p>}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="renewal_notice_days">Renewal Notice (Days) *</Label>
                            <Input id="renewal_notice_days" type="number" min="1" max="365" {...register("renewal_notice_days")} />
                            {errors.renewal_notice_days && <p className="text-sm text-destructive">{errors.renewal_notice_days.message}</p>}
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="description">Description / Scope</Label>
                        <Textarea id="description" placeholder="Contract scope and coverage..." className="min-h-[80px]" {...register("description")} />
                        {errors.description && <p className="text-sm text-destructive">{errors.description.message}</p>}
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="sla_terms">SLA Terms</Label>
                        <Textarea id="sla_terms" placeholder="Include specific SLAs, uptime guarantees, reporting requirements..." className="min-h-[100px]" {...register("sla_terms")} />
                        {errors.sla_terms && <p className="text-sm text-destructive">{errors.sla_terms.message}</p>}
                    </div>

                    <div className="flex justify-end pt-4 border-t">
                        <Button type="button" variant="outline" onClick={() => router.back()} className="mr-3" disabled={submitting}>Cancel</Button>
                        <Button type="submit" disabled={submitting}>
                            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Save Draft Contract
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}
