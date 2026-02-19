import { api } from "./client";
import type { PaginatedResponse, PurchaseRequest } from "@/types/models";

export const prService = {
    list: async (params?: Record<string, unknown>) => {
        const { data } = await api.get<PaginatedResponse<PurchaseRequest>>("/purchase-requests", { params });
        return data;
    },
    get: async (id: string) => {
        const { data } = await api.get<PurchaseRequest>(`/purchase-requests/${id}`);
        return data;
    },
    create: async (body: Record<string, unknown>) => {
        const { data } = await api.post<PurchaseRequest>("/purchase-requests", body);
        return data;
    },
    update: async (id: string, body: Record<string, unknown>) => {
        const { data } = await api.put<PurchaseRequest>(`/purchase-requests/${id}`, body);
        return data;
    },
    remove: async (id: string) => {
        await api.delete(`/purchase-requests/${id}`);
    },
    submit: async (id: string) => {
        const { data } = await api.post<PurchaseRequest>(`/purchase-requests/${id}/submit`);
        return data;
    },
    retract: async (id: string, reason?: string) => {
        const { data } = await api.post<PurchaseRequest>(`/purchase-requests/${id}/retract`, { reason });
        return data;
    },
    approve: async (id: string, comments?: string) => {
        const { data } = await api.post(`/purchase-requests/${id}/approve`, { comments });
        return data;
    },
    reject: async (id: string, comments: string) => {
        const { data } = await api.post(`/purchase-requests/${id}/reject`, { comments });
        return data;
    },
};
