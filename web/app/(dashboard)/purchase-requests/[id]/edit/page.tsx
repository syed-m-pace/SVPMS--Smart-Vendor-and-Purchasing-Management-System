"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Trash2, Loader2, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { prService } from "@/lib/api/purchase-requests";
import { useAuthStore } from "@/lib/stores/auth";
import { formatCurrency } from "@/lib/utils";
import type { PurchaseRequest } from "@/types/models";
import { toast } from "sonner";

function getApiErrorMessage(error: unknown, fallback: string) {
    if (typeof error !== "object" || error === null) return fallback;
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof detail === "string") return detail;
    return fallback;
}

const lineItemSchema = z.object({
    description: z.string().min(3, "Min 3 characters"),
    quantity: z.number().min(1, "Min 1"),
    unit_price_rupees: z.number().min(0.01, "Required"),
    category: z.string().optional(),
});

const editPRSchema = z.object({
    description: z.string().max(1000).optional(),
    justification: z.string().optional(),
    line_items: z.array(lineItemSchema).min(1, "At least one item"),
});

type EditPRForm = z.infer<typeof editPRSchema>;

export default function EditPurchaseRequestPage() {
    const params = useParams();
    const router = useRouter();
    const user = useAuthStore((s) => s.user);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [pr, setPr] = useState<PurchaseRequest | null>(null);

    const {
        register,
        control,
        handleSubmit,
        reset,
        watch,
        formState: { errors },
    } = useForm<EditPRForm>({
        resolver: zodResolver(editPRSchema),
        defaultValues: {
            description: "",
            justification: "",
            line_items: [{ description: "", quantity: 1, unit_price_rupees: 0, category: "" }],
        },
    });

    const { fields, append, remove } = useFieldArray({ control, name: "line_items" });
    const lineItems = watch("line_items");
    const total = useMemo(() => {
        return lineItems.reduce((sum, li) => {
            const lineCents = Math.round((li.quantity || 0) * (li.unit_price_rupees || 0) * 100);
            return sum + lineCents;
        }, 0);
    }, [lineItems]);

    useEffect(() => {
        async function load() {
            setLoading(true);
            try {
                const data = await prService.get(params.id as string);
                setPr(data);
                reset({
                    description: data.description || "",
                    justification: data.justification || "",
                    line_items: data.line_items.map((li) => ({
                        description: li.description,
                        quantity: li.quantity,
                        unit_price_rupees: li.unit_price_cents / 100,
                        category: li.category || "",
                    })),
                });
            } catch {
                toast.error("Failed to load purchase request");
            } finally {
                setLoading(false);
            }
        }
        load();
    }, [params.id, reset]);

    async function onSubmit(values: EditPRForm) {
        if (!pr) return;
        setSaving(true);
        try {
            const updated = await prService.update(pr.id, {
                description: values.description || null,
                justification: values.justification || null,
                line_items: values.line_items.map((li) => ({
                    description: li.description,
                    quantity: li.quantity,
                    unit_price_cents: Math.round(li.unit_price_rupees * 100),
                    category: li.category || null,
                })),
            });
            toast.success(`Updated ${updated.pr_number}`);
            router.push(`/purchase-requests/${updated.id}`);
        } catch (error: unknown) {
            toast.error(getApiErrorMessage(error, "Failed to update PR"));
        } finally {
            setSaving(false);
        }
    }

    if (loading) {
        return (
            <div className="flex justify-center py-20">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" />
            </div>
        );
    }

    if (!pr) return <p>Purchase request not found</p>;

    if (user?.id && user.id !== pr.requester_id) {
        return (
            <div className="space-y-4 max-w-3xl">
                <Button variant="ghost" onClick={() => router.push(`/purchase-requests/${pr.id}`)}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to PR
                </Button>
                <Card>
                    <CardContent className="pt-6">
                        <p className="text-lg font-medium">Only the requester can edit this purchase request.</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (pr.status !== "DRAFT") {
        return (
            <div className="space-y-4 max-w-3xl">
                <Button variant="ghost" onClick={() => router.push(`/purchase-requests/${pr.id}`)}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to PR
                </Button>
                <Card>
                    <CardContent className="pt-6">
                        <p className="text-lg font-medium">Only DRAFT purchase requests can be edited.</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Edit {pr.pr_number}</h1>
                    <p className="text-muted-foreground mt-1">Update details before submission</p>
                </div>
                <Button variant="ghost" onClick={() => router.push(`/purchase-requests/${pr.id}`)}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                </Button>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <Card>
                    <CardHeader><CardTitle className="text-lg">Request Details</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">Description</label>
                            <Textarea {...register("description")} placeholder="Additional details" rows={3} />
                            {errors.description && <p className="text-sm text-destructive mt-1">{errors.description.message}</p>}
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">Justification</label>
                            <Textarea {...register("justification")} placeholder="Business justification" rows={3} />
                            {errors.justification && <p className="text-sm text-destructive mt-1">{errors.justification.message}</p>}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-lg">Line Items</CardTitle>
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => append({ description: "", quantity: 1, unit_price_rupees: 0, category: "" })}
                        >
                            <Plus className="w-4 h-4 mr-2" />
                            Add Item
                        </Button>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {fields.map((field, idx) => (
                            <div key={field.id} className="p-4 border rounded-lg space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="font-medium text-sm">Item {idx + 1}</span>
                                    {fields.length > 1 && (
                                        <Button type="button" variant="ghost" size="sm" onClick={() => remove(idx)}>
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    )}
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                                    <div className="md:col-span-2">
                                        <label className="block text-xs font-medium mb-1">Description *</label>
                                        <Input {...register(`line_items.${idx}.description`)} placeholder="Item description" />
                                        {errors.line_items?.[idx]?.description && (
                                            <p className="text-xs text-destructive mt-1">{errors.line_items[idx]?.description?.message}</p>
                                        )}
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium mb-1">Quantity *</label>
                                        <Input
                                            type="number"
                                            min="1"
                                            {...register(`line_items.${idx}.quantity`, { valueAsNumber: true })}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium mb-1">Unit Price (₹) *</label>
                                        <Input
                                            type="number"
                                            step="0.01"
                                            placeholder="0.00"
                                            {...register(`line_items.${idx}.unit_price_rupees`, { valueAsNumber: true })}
                                        />
                                    </div>
                                </div>
                                <div className="text-right text-sm text-muted-foreground">
                                    Subtotal: {formatCurrency(Math.round((lineItems[idx]?.quantity || 0) * (lineItems[idx]?.unit_price_rupees || 0) * 100))}
                                </div>
                            </div>
                        ))}
                        <div className="flex justify-end pt-4 border-t">
                            <div className="text-right">
                                <p className="text-sm text-muted-foreground">Total Amount</p>
                                <p className="text-2xl font-bold font-mono">{formatCurrency(total)}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <div className="flex justify-end gap-3">
                    <Button type="button" variant="outline" onClick={() => router.push(`/purchase-requests/${pr.id}`)} disabled={saving}>
                        Cancel
                    </Button>
                    <Button type="submit" disabled={saving}>
                        {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save Changes
                    </Button>
                </div>
            </form>
        </div>
    );
}
