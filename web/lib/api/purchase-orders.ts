import { api } from "./client";
import type { PaginatedResponse, PurchaseOrder, PurchaseOrderReady } from "@/types/models";

type QueryParams = Record<string, string | number | boolean | null | undefined>;

export const poService = {
    list: async (params?: QueryParams) => {
        const { data } = await api.get<PaginatedResponse<PurchaseOrder>>("/purchase-orders", { params });
        return data;
    },
    ready: async (params?: QueryParams) => {
        const { data } = await api.get<PaginatedResponse<PurchaseOrderReady>>("/purchase-orders/ready", { params });
        return data;
    },
    get: async (id: string) => {
        const { data } = await api.get<PurchaseOrder>(`/purchase-orders/${id}`);
        return data;
    },
    create: async (body: {
        pr_id: string;
        vendor_id: string;
        expected_delivery_date?: string | null;
        terms_and_conditions?: string | null;
    }) => {
        const { data } = await api.post<PurchaseOrder>("/purchase-orders", body);
        return data;
    },
};
