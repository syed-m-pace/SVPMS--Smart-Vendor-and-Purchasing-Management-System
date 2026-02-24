import { z } from "zod";

export const invoiceUploadSchema = z.object({
    po_id: z.string({ error: "Please select a Purchase Order" }).min(1, "Please select a Purchase Order"),
    invoice_number: z.string({ error: "Invoice number is required" }).min(1, "Invoice number is required"),
    invoice_date: z.string({ error: "Invoice date is required" }).min(1, "Invoice date is required"),
    total_amount: z
        .number({ error: "Total amount is required" })
        .min(0.01, "Total amount must be greater than 0"),
});

export type InvoiceUploadFormData = z.infer<typeof invoiceUploadSchema>;
