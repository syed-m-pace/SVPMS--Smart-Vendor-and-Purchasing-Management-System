"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm, useFieldArray, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2, Loader2 } from "lucide-react";
import { rfqService } from "@/lib/api/rfqs";
import { toast } from "sonner";

const lineItemSchema = z.object({
    description: z.string().min(3, "Min 3 characters"),
    quantity: z.coerce.number().min(1, "Min 1"),
    specifications: z.string().optional(),
});

const rfqSchema = z.object({
    title: z.string().min(3, "Title required").max(200),
    deadline: z.string().min(1, "Deadline required"),
    pr_id: z.string().optional(),
    line_items: z.array(lineItemSchema).min(1, "At least one item"),
});

type RFQForm = z.infer<typeof rfqSchema>;

export default function NewRFQPage() {
    const router = useRouter();
    const [submitting, setSubmitting] = useState(false);

    const { register, control, handleSubmit, formState: { errors } } = useForm<RFQForm>({
        resolver: zodResolver(rfqSchema) as any,
        defaultValues: {
            title: "",
            deadline: "",
            pr_id: "",
            line_items: [{ description: "", quantity: 1, specifications: "" }],
        },
    });

    const { fields, append, remove } = useFieldArray({ control, name: "line_items" });

    async function onSubmit(data: RFQForm) {
        setSubmitting(true);
        try {
            // Convert datetime-local to ISO 8601
            const isoDeadline = new Date(data.deadline).toISOString();

            const payload = {
                title: data.title,
                pr_id: data.pr_id || undefined,
                deadline: isoDeadline,
                line_items: data.line_items,
            };

            const rfq = await rfqService.create(payload as any);
            toast.success(`Created RFQ ${rfq.rfq_number}. Vendors have been notified!`);
            router.push(`/purchase-orders?tab=rfqs`);
        } catch (e: any) {
            toast.error(e.response?.data?.detail?.error?.message || e.response?.data?.detail || "Failed to create RFQ");
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-center gap-4 mb-6">
                <Button variant="ghost" className="mb-1" onClick={() => router.back()}>
                    &larr; Back
                </Button>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Issue New RFQ</h1>
                    <p className="text-muted-foreground mt-1">Issue a Request for Quotation to all active vendors</p>
                </div>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <Card>
                    <CardHeader><CardTitle className="text-lg">RFQ Details</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Title *</label>
                                <Input placeholder="e.g. Laptops Q3" {...register("title")} />
                                {errors.title && <p className="text-sm text-red-500 mt-1">{errors.title.message}</p>}
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2">Deadline *</label>
                                <Input type="datetime-local" {...register("deadline")} />
                                {errors.deadline && <p className="text-sm text-red-500 mt-1">{errors.deadline.message}</p>}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-lg">Line Items</CardTitle>
                        <Button type="button" variant="outline" size="sm" onClick={() => append({ description: "", quantity: 1, specifications: "" })}>
                            <Plus className="mr-2 h-4 w-4" /> Add Item
                        </Button>
                    </CardHeader>
                    <CardContent className="space-y-4 pt-4">
                        {fields.map((field, index) => (
                            <div key={field.id} className="grid grid-cols-[1fr_100px_40px] gap-4 items-start border-b pb-4 last:border-0 last:pb-0">
                                <div className="space-y-4">
                                    <div>
                                        <Input placeholder="Description" {...register(`line_items.${index}.description` as const)} />
                                        {errors.line_items?.[index]?.description && (
                                            <p className="text-sm text-red-500 mt-1">{errors.line_items[index]?.description?.message}</p>
                                        )}
                                    </div>
                                    <div>
                                        <Textarea placeholder="Specifications (optional)" className="h-20" {...register(`line_items.${index}.specifications` as const)} />
                                    </div>
                                </div>
                                <div>
                                    <Input type="number" min="1" placeholder="Qty" {...register(`line_items.${index}.quantity` as const)} />
                                    {errors.line_items?.[index]?.quantity && (
                                        <p className="text-sm text-red-500 mt-1">{errors.line_items[index]?.quantity?.message}</p>
                                    )}
                                </div>
                                <Button type="button" variant="ghost" size="icon" className="text-red-500 hover:text-red-600 hover:bg-red-50" onClick={() => remove(index)} disabled={fields.length === 1}>
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                        ))}
                    </CardContent>
                </Card>

                <div className="flex justify-end gap-3">
                    <Button type="button" variant="outline" onClick={() => router.back()}>Cancel</Button>
                    <Button type="submit" disabled={submitting}>
                        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Issue RFQ to Vendors
                    </Button>
                </div>
            </form>
        </div>
    );
}
