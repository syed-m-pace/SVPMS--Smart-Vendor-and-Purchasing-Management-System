import { api } from "./client";
import type { PaginatedResponse, RFQ } from "@/types/models";

export const rfqService = {
    list: async (params?: Record<string, string | number | boolean | null | undefined>) => {
        const { data } = await api.get<PaginatedResponse<RFQ>>("/rfqs", { params });
        return data;
    },
    create: async (body: { title: string; pr_id: string; deadline: string; line_items: any[] }) => {
        const { data } = await api.post<RFQ>("/rfqs", body);
        return data;
    }
};
