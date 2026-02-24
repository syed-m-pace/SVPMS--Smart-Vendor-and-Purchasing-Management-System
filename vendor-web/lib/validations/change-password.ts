import { z } from "zod";

export const changePasswordSchema = z
    .object({
        current_password: z.string().min(1, "Current password is required"),
        new_password: z
            .string()
            .min(8, "Password must be at least 8 characters")
            .regex(/[A-Z]/, "Must contain an uppercase letter")
            .regex(/[a-z]/, "Must contain a lowercase letter")
            .regex(/[0-9]/, "Must contain a digit")
            .regex(/[!@#$%^&*]/, "Must contain a special character"),
        confirm_password: z.string().min(1, "Please confirm your password"),
    })
    .refine((data) => data.new_password === data.confirm_password, {
        message: "Passwords do not match",
        path: ["confirm_password"],
    });

export type ChangePasswordFormData = z.infer<typeof changePasswordSchema>;
