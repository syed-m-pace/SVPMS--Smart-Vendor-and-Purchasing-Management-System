import { api } from "./client";
import type { PaginatedResponse, Vendor } from "@/types/models";

export const vendorService = {
    list: async (params?: Record<string, any>) => {
        const { data } = await api.get<PaginatedResponse<Vendor>>("/vendors", { params });
        return data;
    },
    get: async (id: string) => {
        const { data } = await api.get<Vendor>(`/vendors/${id}`);
        return data;
    },
    create: async (body: Partial<Vendor>) => {
        const { data } = await api.post<Vendor>("/vendors", body);
        return data;
    },
    update: async (id: string, body: Partial<Vendor>) => {
        const { data } = await api.patch<Vendor>(`/vendors/${id}`, body);
        return data;
    },
    approve: async (id: string, contract_ids?: string[]) => {
        const payload = contract_ids && contract_ids.length > 0 ? { contract_ids } : {};
        const { data } = await api.post<Vendor>(`/vendors/${id}/approve`, payload);
        return data;
    },
    block: async (id: string, reason: string) => {
        const { data } = await api.post<Vendor>(`/vendors/${id}/block`, { reason });
        return data;
    },
    unblock: async (id: string) => {
        const { data } = await api.post<Vendor>(`/vendors/${id}/unblock`);
        return data;
    },
};
