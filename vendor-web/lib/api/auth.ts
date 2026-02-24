import { api, authApi } from "./client";

export const authService = {
    changePassword: async (currentPassword: string, newPassword: string) => {
        const { data } = await api.post("/auth/change-password", {
            current_password: currentPassword,
            new_password: newPassword,
        });
        return data;
    },
};
