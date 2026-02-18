"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm, useFieldArray, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2, Loader2 } from "lucide-react";
import { prService } from "@/lib/api/purchase-requests";
import { departmentService } from "@/lib/api/services";
import { formatCurrency } from "@/lib/utils";
import { toast } from "sonner";
import type { Department } from "@/types/models";

const lineItemSchema = z.object({
    line_number: z.number(),
    description: z.string().min(3, "Min 3 characters"),
    quantity: z.number().min(1, "Min 1"),
    unit_price_cents: z.number().min(1, "Required"),
    category: z.string().optional(),
});

const prSchema = z.object({
    department_id: z.string().min(1, "Select department"),
    title: z.string().min(3, "Title required").max(200),
    description: z.string().max(1000).optional(),
    line_items: z.array(lineItemSchema).min(1, "At least one item"),
});

type PRForm = z.infer<typeof prSchema>;

export default function NewPurchaseRequestPage() {
    const router = useRouter();
    const [departments, setDepartments] = useState<Department[]>([]);
    const [submitting, setSubmitting] = useState(false);

    const { register, control, handleSubmit, watch, formState: { errors } } = useForm<PRForm>({
        resolver: zodResolver(prSchema),
        defaultValues: {
            department_id: "",
            line_items: [{ line_number: 1, description: "", quantity: 1, unit_price_cents: 0 }],
        },
    });

    console.log("Current Dept:", watch("department_id"));
    console.log("Errors:", errors);

    const { fields, append, remove } = useFieldArray({ control, name: "line_items" });
    const lineItems = watch("line_items");
    const total = lineItems.reduce((sum, li) => sum + (li.quantity || 0) * (li.unit_price_cents || 0), 0);

    useEffect(() => {
        departmentService.list().then((r) => {
            console.log("Departments loaded:", r.data);
            setDepartments(r.data);
        }).catch((err) => console.error("Failed to load departments", err));
    }, []);

    async function onSubmit(data: PRForm) {
        setSubmitting(true);
        try {
            const pr = await prService.create(data);
            toast.success(`Created ${pr.pr_number}`);
            router.push(`/purchase-requests/${pr.id}`);
        } catch (e: any) {
            toast.error(e.response?.data?.detail?.error?.message || "Failed to create PR");
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">New Purchase Request</h1>
                <p className="text-muted-foreground mt-1">Create a new purchase request for approval</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <Card>
                    <CardHeader><CardTitle className="text-lg">Basic Information</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Department *</label>
                                <Controller
                                    name="department_id"
                                    control={control}
                                    render={({ field }) => (
                                        <select
                                            {...field}
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 appearance-none"
                                        >
                                            <option value="">Select department</option>
                                            {departments.map((d) => (
                                                <option key={d.id} value={d.id}>
                                                    {d.name} ({d.code})
                                                </option>
                                            ))}
                                        </select>
                                    )}
                                />
                                {errors.department_id && <p className="text-sm text-destructive mt-1">{errors.department_id.message}</p>}
                                <p className="text-xs text-muted-foreground mt-1">Found {departments.length} departments</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2">Title *</label>
                                <Input {...register("title")} placeholder="Brief title" />
                                {errors.title && <p className="text-sm text-destructive mt-1">{errors.title.message}</p>}
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">Description</label>
                            <Textarea {...register("description")} placeholder="Additional details" rows={3} />
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-lg">Line Items</CardTitle>
                        <Button type="button" variant="outline" size="sm" onClick={() => append({ line_number: fields.length + 1, description: "", quantity: 1, unit_price_cents: 0 })}>
                            <Plus className="w-4 h-4 mr-2" />Add Item
                        </Button>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {fields.map((field, idx) => (
                            <div key={field.id} className="p-4 border rounded-lg space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="font-medium text-sm">Item {idx + 1}</span>
                                    {fields.length > 1 && (
                                        <Button type="button" variant="ghost" size="sm" onClick={() => remove(idx)}><Trash2 className="h-4 w-4" /></Button>
                                    )}
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                    <div className="md:col-span-1">
                                        <label className="block text-xs font-medium mb-1">Description *</label>
                                        <Input {...register(`line_items.${idx}.description`)} placeholder="Item description" />
                                        {errors.line_items?.[idx]?.description && <p className="text-xs text-destructive mt-1">{errors.line_items[idx]?.description?.message}</p>}
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium mb-1">Quantity *</label>
                                        <Input type="number" {...register(`line_items.${idx}.quantity`, { valueAsNumber: true })} min="1" />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium mb-1">Unit Price (₹) *</label>
                                        <Input type="number" step="0.01" {...register(`line_items.${idx}.unit_price_cents`, { setValueAs: (v: string) => Math.round(parseFloat(v || "0") * 100) })} placeholder="0.00" />
                                    </div>
                                </div>
                                <div className="text-right text-sm text-muted-foreground">
                                    Subtotal: {formatCurrency((lineItems[idx]?.quantity || 0) * (lineItems[idx]?.unit_price_cents || 0))}
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
                    <Button type="button" variant="outline" onClick={() => router.back()} disabled={submitting}>Cancel</Button>
                    <Button type="submit" disabled={submitting}>
                        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Create Purchase Request
                    </Button>
                </div>
            </form>
        </div>
    );
}
