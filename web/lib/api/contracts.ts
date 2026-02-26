import { api } from "./client";
import type { PaginatedResponse, Contract } from "@/types/models";

type QueryParams = Record<string, string | number | boolean | null | undefined>;

export const contractService = {
    list: async (params?: QueryParams) => {
        const { data } = await api.get<PaginatedResponse<Contract>>("/contracts", { params });
        return data;
    },
    get: async (id: string) => {
        const { data } = await api.get<Contract>(`/contracts/${id}`);
        return data;
    },
    create: async (body: Record<string, unknown>) => {
        const { data } = await api.post<Contract>("/contracts", body);
        return data;
    },
    update: async (id: string, body: Record<string, unknown>) => {
        const { data } = await api.patch<Contract>(`/contracts/${id}`, body);
        return data;
    },
    activate: async (id: string) => {
        const { data } = await api.post<Contract>(`/contracts/${id}/activate`);
        return data;
    },
    terminate: async (id: string, reason: string) => {
        const { data } = await api.post<Contract>(`/contracts/${id}/terminate`, { reason });
        return data;
    },
    assignVendors: async (id: string, vendor_ids: string[]) => {
        const { data } = await api.post(`/contracts/${id}/assign`, { vendor_ids });
        return data;
    },
    delete: async (id: string) => {
        await api.delete(`/contracts/${id}`);
    }
};
