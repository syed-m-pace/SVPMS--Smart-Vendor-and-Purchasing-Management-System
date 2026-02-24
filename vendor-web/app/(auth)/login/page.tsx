"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { useAuthStore } from "@/lib/stores/auth";
import { toast } from "sonner";

export default function LoginPage() {
    const router = useRouter();
    const login = useAuthStore((s) => s.login);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await login(email, password);
            toast.success("Welcome back!");
            router.push("/");
        } catch (err: any) {
            const msg = err?.response?.data?.detail || err?.message || "Login failed";
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    };

    const fillDemo = () => {
        setEmail("syedmuheeb2001@gmail.com");
        setPassword("SvpmsTest123!");
    };

    return (
        <div className="w-full max-w-md px-4">
            <div className="text-center mb-8">
                <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-white font-bold text-2xl mb-4">
                    V
                </div>
                <h1 className="text-2xl font-bold text-foreground">SVPMS Vendor Portal</h1>
                <p className="text-sm text-muted-foreground mt-1">Sign in to manage your orders and invoices</p>
            </div>

            <Card className="p-6">
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input
                            id="email"
                            type="email"
                            placeholder="vendor@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            autoFocus
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="password">Password</Label>
                        <div className="relative">
                            <Input
                                id="password"
                                type={showPassword ? "text" : "password"}
                                placeholder="Enter your password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                            >
                                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </button>
                        </div>
                    </div>

                    <Button type="submit" className="w-full" disabled={loading}>
                        {loading ? (
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        ) : (
                            <>
                                <LogIn className="h-4 w-4 mr-2" />
                                Sign In
                            </>
                        )}
                    </Button>
                </form>

                <div className="mt-4 pt-4 border-t">
                    <button
                        onClick={fillDemo}
                        className="w-full text-xs text-muted-foreground hover:text-foreground transition-colors text-center"
                    >
                        Use demo credentials (syedmuheeb2001@gmail.com / SvpmsTest123!)
                    </button>
                </div>
            </Card>
        </div>
    );
}
