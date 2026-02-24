import { api } from "./client";
import type { PaginatedResponse, RFQ, RFQBid } from "@/types/models";

type QueryParams = Record<string, string | number | boolean | null | undefined>;

export const rfqService = {
    list: async (params?: QueryParams) => {
        const { data } = await api.get<PaginatedResponse<RFQ>>("/rfqs", { params });
        return data;
    },
    get: async (id: string) => {
        const { data } = await api.get<RFQ>(`/rfqs/${id}`);
        return data;
    },
    submitBid: async (rfqId: string, bid: { total_cents: number; delivery_days: number; notes?: string }) => {
        const { data } = await api.post<RFQBid>(`/rfqs/${rfqId}/bids`, bid);
        return data;
    },
    listBids: async (rfqId: string) => {
        const { data } = await api.get<RFQBid[]>(`/rfqs/${rfqId}/bids`);
        return data;
    },
};
