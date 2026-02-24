import { api } from "./client";

export interface SpendAnalytics {
    total_spend_cents: number;
    by_month: Array<{ month: string; amount_cents: number }>;
    by_po: Array<{ po_number: string; amount_cents: number }>;
    currency: string;
}

export const analyticsService = {
    getSpend: async (params?: Record<string, string | number | null | undefined>) => {
        const { data } = await api.get<SpendAnalytics>("/analytics/spend", { params });
        return data;
    },
};
