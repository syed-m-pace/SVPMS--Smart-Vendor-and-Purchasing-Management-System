import { api } from "./client";
import type { DashboardStats, PaginatedResponse, PurchaseOrder } from "@/types/models";

export const dashboardService = {
    getStats: async () => {
        const { data } = await api.get<DashboardStats>("/dashboard/stats");
        return data;
    },
    getRecentPOs: async () => {
        const { data } = await api.get<PaginatedResponse<PurchaseOrder>>("/purchase-orders", {
            params: { per_page: 5, page: 1 },
        });
        return data;
    },
};
