import { api } from "./client";
import type { Vendor, VendorScorecard } from "@/types/models";

export const vendorService = {
    getMe: async () => {
        const { data } = await api.get<Vendor>("/vendors/me");
        return data;
    },
    getScorecard: async (vendorId: string) => {
        const { data } = await api.get<VendorScorecard>(`/vendors/${vendorId}/scorecard`);
        return data;
    },
};
