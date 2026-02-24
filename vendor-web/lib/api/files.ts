import { api } from "./client";

export const fileService = {
    upload: async (file: File) => {
        const formData = new FormData();
        formData.append("file", file);
        const { data } = await api.post<{ file_key: string; url: string }>("/files/upload", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });
        return data;
    },
    getPresignedUrl: async (fileKey: string) => {
        const { data } = await api.get<{ url: string }>(`/files/${encodeURIComponent(fileKey)}`);
        return data;
    },
};
