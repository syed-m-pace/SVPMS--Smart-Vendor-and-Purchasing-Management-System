import { api } from "./client";
import type { PaginatedResponse, Invoice } from "@/types/models";

type QueryParams = Record<string, string | number | boolean | null | undefined>;

export interface InvoiceCreateRequest {
    po_id: string;
    invoice_number: string;
    invoice_date: string;
    total_cents: number;
    document_key?: string;
    line_items?: Array<{ description: string; quantity: number; unit_price_cents: number }>;
}

export const invoiceService = {
    list: async (params?: QueryParams) => {
        const { data } = await api.get<PaginatedResponse<Invoice>>("/invoices", { params });
        return data;
    },
    get: async (id: string) => {
        const { data } = await api.get<Invoice>(`/invoices/${id}`);
        return data;
    },
    create: async (body: InvoiceCreateRequest) => {
        const { data } = await api.post<Invoice>("/invoices", body);
        return data;
    },
    dispute: async (id: string, reason?: string) => {
        const { data } = await api.post<Invoice>(`/invoices/${id}/dispute`, { reason });
        return data;
    },
};
