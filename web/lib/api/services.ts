import { api } from "./client";
import type { PaginatedResponse, Budget, Department, Approval, Receipt } from "@/types/models";

export const budgetService = {
    list: async (params?: Record<string, any>) => {
        const { data } = await api.get<PaginatedResponse<Budget>>("/budgets", { params });
        return data;
    },
    update: async (id: string, payload: Partial<Budget>) => {
        const { data } = await api.patch<Budget>(`/budgets/${id}`, payload);
        return data;
    },
};

export const departmentService = {
    list: async () => {
        const { data } = await api.get<PaginatedResponse<Department>>("/departments");
        return data;
    },
};

export const approvalService = {
    listPending: async () => {
        const { data } = await api.get<PaginatedResponse<Approval>>("/approvals", {
            params: { status: "PENDING" },
        });
        return data;
    },
    approve: async (id: string, comments?: string) => {
        const { data } = await api.post(`/approvals/${id}/approve`, { comments });
        return data;
    },
    reject: async (id: string, comments: string) => {
        const { data } = await api.post(`/approvals/${id}/reject`, { comments });
        return data;
    },
};

export const receiptService = {
    list: async (params?: Record<string, any>) => {
        const { data } = await api.get<PaginatedResponse<Receipt>>("/receipts", { params });
        return data;
    },
    get: async (id: string) => {
        const { data } = await api.get<Receipt>(`/receipts/${id}`);
        return data;
    },
    create: async (body: any) => {
        const { data } = await api.post<Receipt>("/receipts", body);
        return data;
    },
};
