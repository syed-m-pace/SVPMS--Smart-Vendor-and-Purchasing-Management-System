import { api } from "./client";
import type { PaginatedResponse, PurchaseOrder } from "@/types/models";

export const poService = {
    list: async (params?: Record<string, any>) => {
        const { data } = await api.get<PaginatedResponse<PurchaseOrder>>("/purchase-orders", { params });
        return data;
    },
    get: async (id: string) => {
        const { data } = await api.get<PurchaseOrder>(`/purchase-orders/${id}`);
        return data;
    },
};
