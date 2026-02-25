"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Send } from "lucide-react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { rfqService } from "@/lib/api/rfqs";
import { useAuthStore } from "@/lib/stores/auth";
import { bidSchema, type BidFormData } from "@/lib/validations/bid";
import { formatCurrency } from "@/lib/utils";
import { toast } from "sonner";
import type { RFQ } from "@/types/models";

export default function BidFormPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();
    const vendor = useAuthStore((s) => s.vendor);
    const [rfq, setRfq] = useState<RFQ | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    const {
        register,
        handleSubmit,
        setValue,
        control,
        formState: { errors },
    } = useForm<BidFormData>({
        resolver: zodResolver(bidSchema),
    });

    const watchedAmount = useWatch({ control, name: "total_amount" });

    useEffect(() => {
        rfqService.get(id).then((data) => {
            setRfq(data);
            // Pre-fill if existing bid
            const myBid = data.bids?.find((b) => vendor && b.vendor_id === vendor.id);
            if (myBid) {
                setValue("total_amount", myBid.total_cents / 100);
                setValue("delivery_days", myBid.delivery_days || 0);
                setValue("notes", myBid.notes || "");
            }
        }).catch(() => toast.error("Failed to load RFQ")).finally(() => setLoading(false));
    }, [id, vendor, setValue]);

    const onSubmit = async (formData: BidFormData) => {
        setSubmitting(true);
        try {
            const totalCents = Math.round(formData.total_amount * 100);
            await rfqService.submitBid(id, {
                total_cents: totalCents,
                delivery_days: formData.delivery_days,
                notes: formData.notes,
            });
            toast.success("Bid submitted successfully");
            router.push(`/rfqs/${id}`);
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || "Failed to submit bid");
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" />
            </div>
        );
    }

    if (!rfq) return null;

    const myBid = rfq.bids?.find((b) => vendor && b.vendor_id === vendor.id);

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.push(`/rfqs/${id}`)}>
                    <ArrowLeft className="h-5 w-5" />
                </Button>
                <div>
                    <h1 className="text-2xl font-bold">{myBid ? "Update Bid" : "Submit Bid"}</h1>
                    <p className="text-muted-foreground">{rfq.title} — {rfq.rfq_number}</p>
                </div>
            </div>

            {/* RFQ Summary */}
            <Card className="p-5">
                <h3 className="font-semibold mb-3">RFQ Summary</h3>
                <p className="text-sm text-muted-foreground mb-2">{rfq.description || "No description"}</p>
                {rfq.budget_cents && (
                    <p className="text-sm">Budget: <span className="font-medium">{formatCurrency(rfq.budget_cents)}</span></p>
                )}
                {rfq.line_items && rfq.line_items.length > 0 && (
                    <div className="mt-3 pt-3 border-t">
                        <p className="text-xs text-muted-foreground mb-2">Line Items:</p>
                        <ul className="space-y-1">
                            {rfq.line_items.map((item, i) => (
                                <li key={item.id} className="text-sm">
                                    {i + 1}. {item.description} — Qty: {item.quantity}
                                    {item.specifications && ` (${item.specifications})`}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </Card>

            {/* Bid Form */}
            <Card className="p-5">
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="total_amount">Total Bid Amount (INR)</Label>
                        <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">&#8377;</span>
                            <Input
                                id="total_amount"
                                type="number"
                                step="0.01"
                                min="0"
                                placeholder="5,000.00"
                                className="pl-7"
                                {...register("total_amount", { valueAsNumber: true })}
                            />
                        </div>
                        {watchedAmount > 0 && (
                            <p className="text-xs text-muted-foreground">
                                = {formatCurrency(Math.round(watchedAmount * 100))}
                            </p>
                        )}
                        {errors.total_amount && (
                            <p className="text-xs text-destructive">{errors.total_amount.message}</p>
                        )}
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="delivery_days">Lead Time (Days)</Label>
                        <Input
                            id="delivery_days"
                            type="number"
                            placeholder="e.g., 14"
                            {...register("delivery_days", { valueAsNumber: true })}
                        />
                        {errors.delivery_days && (
                            <p className="text-xs text-destructive">{errors.delivery_days.message}</p>
                        )}
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="notes">Notes (Optional)</Label>
                        <Textarea
                            id="notes"
                            placeholder="Additional comments about your bid..."
                            rows={3}
                            {...register("notes")}
                        />
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
                                    <Send className="h-4 w-4 mr-2" />
                                    {myBid ? "Update Bid" : "Submit Bid"}
                                </>
                            )}
                        </Button>
                    </div>
                </form>
            </Card>
        </div>
    );
}
