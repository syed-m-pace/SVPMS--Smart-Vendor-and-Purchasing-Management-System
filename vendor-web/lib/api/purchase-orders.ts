import { api } from "./client";
import type { PaginatedResponse, PurchaseOrder } from "@/types/models";

type QueryParams = Record<string, string | number | boolean | null | undefined>;

export const poService = {
    list: async (params?: QueryParams) => {
        const { data } = await api.get<PaginatedResponse<PurchaseOrder>>("/purchase-orders", { params });
        return data;
    },
    get: async (id: string) => {
        const { data } = await api.get<PurchaseOrder>(`/purchase-orders/${id}`);
        return data;
    },
    acknowledge: async (id: string, expectedDeliveryDate: string) => {
        const { data } = await api.post<PurchaseOrder>(`/purchase-orders/${id}/acknowledge`, {
            expected_delivery_date: expectedDeliveryDate,
        });
        return data;
    },
};
