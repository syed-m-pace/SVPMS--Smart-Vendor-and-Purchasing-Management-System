"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Lock, Mail, Loader2 } from "lucide-react";

export default function LoginPage() {
    const router = useRouter();
    const login = useAuthStore((s) => s.login);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await login(email, password);
            router.push("/");
        } catch {
            setError("Invalid email or password");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="w-full max-w-md">
            {/* Branding */}
            <div className="text-center mb-8">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-white shadow-lg shadow-primary/25">
                    <span className="text-2xl font-bold">S</span>
                </div>
                <h1 className="text-3xl font-bold tracking-tight">Welcome back</h1>
                <p className="mt-2 text-muted-foreground">
                    Sign in to SVPMS Procurement Portal
                </p>
            </div>

            {/* Card */}
            <div className="rounded-2xl border bg-card p-8 shadow-xl shadow-black/5">
                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <label className="block text-sm font-medium mb-2">Email</label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@company.com"
                                className="pl-10"
                                required
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">Password</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                className="pl-10"
                                required
                            />
                        </div>
                    </div>

                    {error && (
                        <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                            {error}
                        </div>
                    )}

                    <Button
                        type="submit"
                        className="w-full h-11 text-base"
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Signing in...
                            </>
                        ) : (
                            "Sign in"
                        )}
                    </Button>
                </form>

                {/* Demo credentials */}
                <div className="mt-6 rounded-lg bg-muted/50 p-4">
                    <p className="text-xs font-medium text-muted-foreground mb-2">
                        Demo credentials
                    </p>
                    <div className="space-y-1 text-xs text-muted-foreground">
                        <p>
                            <span className="font-mono">eng.manager@acme.com</span>
                        </p>
                        <p className="mt-2">
                            <span className="font-semibold text-xs text-foreground">Admin:</span><br />
                            <span className="font-mono">admin@acme.com</span>
                        </p>
                        <p className="mt-2 border-t pt-2">
                            <span className="font-mono">SvpmsTest123!</span>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
