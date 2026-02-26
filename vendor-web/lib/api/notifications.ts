import { api } from "./client";
import { AppNotification } from "@/types/models";

export const notificationService = {
    async getRecent(): Promise<AppNotification[]> {
        const { data } = await api.get<AppNotification[]>("/notifications");
        return data;
    },

    async markRead(id: string): Promise<AppNotification> {
        const { data } = await api.post<AppNotification>(`/notifications/${id}/read`);
        return data;
    }
};
