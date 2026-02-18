import { api } from "./client";
import type { PaginatedResponse, Invoice } from "@/types/models";

export const invoiceService = {
    list: async (params?: Record<string, any>) => {
        const { data } = await api.get<PaginatedResponse<Invoice>>("/invoices", { params });
        return data;
    },
    get: async (id: string) => {
        const { data } = await api.get<Invoice>(`/invoices/${id}`);
        return data;
    },
    override: async (id: string, reason: string) => {
        const { data } = await api.post(`/invoices/${id}/override`, { reason });
        return data;
    },
};
