import { api } from "./client";
import type { PaginatedResponse, RFQ, PurchaseOrder } from "@/types/models";

export const rfqService = {
    list: async (params?: Record<string, string | number | boolean | null | undefined>) => {
        const { data } = await api.get<PaginatedResponse<RFQ>>("/rfqs", { params });
        return data;
    },
    create: async (body: { title: string; pr_id?: string; deadline: string; line_items: any[] }) => {
        const { data } = await api.post<RFQ>("/rfqs", body);
        return data;
    },
    get: async (id: string) => {
        const { data } = await api.get<RFQ>(`/rfqs/${id}`);
        return data;
    },
    award: async (rfqId: string, bidId: string) => {
        const { data } = await api.post<PurchaseOrder>(`/rfqs/${rfqId}/award`, { bid_id: bidId });
        return data;
    },
    close: async (rfqId: string) => {
        const { data } = await api.post<RFQ>(`/rfqs/${rfqId}/close`);
        return data;
    },
};
