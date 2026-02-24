import { api } from "./client";
import type { PaginatedResponse, Contract } from "@/types/models";

type QueryParams = Record<string, string | number | boolean | null | undefined>;

export const contractService = {
    list: async (params?: QueryParams) => {
        const { data } = await api.get<PaginatedResponse<Contract>>("/contracts", { params });
        return data;
    },
};
