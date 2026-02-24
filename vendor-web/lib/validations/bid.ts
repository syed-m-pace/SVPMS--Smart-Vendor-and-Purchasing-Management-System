import { z } from "zod";

export const bidSchema = z.object({
    total_cents: z
        .number({ error: "Bid amount is required" })
        .min(1, "Bid amount must be greater than 0"),
    delivery_days: z
        .number({ error: "Lead time is required" })
        .min(1, "Lead time must be at least 1 day"),
    notes: z.string().optional(),
});

export type BidFormData = z.infer<typeof bidSchema>;
