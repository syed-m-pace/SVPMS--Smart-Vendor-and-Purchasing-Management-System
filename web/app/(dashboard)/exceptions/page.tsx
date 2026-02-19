"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Loader2, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { invoiceService } from "@/lib/api/invoices";
import { formatCurrency } from "@/lib/utils";
import type { Invoice } from "@/types/models";
import { toast } from "sonner";
import { isAxiosError } from "axios";

export default function ExceptionsPage() {
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [loading, setLoading] = useState(true);
    const [resolving, setResolving] = useState<string | null>(null);

    useEffect(() => {
        invoiceService.list({ status: "EXCEPTION" }).then((r) => setInvoices(r.data)).catch(() => { }).finally(() => setLoading(false));
    }, []);

    const getErrorMessage = (error: unknown, fallback: string) => {
        if (isAxiosError(error)) {
            const detail = error.response?.data?.detail;
            if (typeof detail === "string") return detail;
            const nested = error.response?.data?.detail?.error?.message;
            if (typeof nested === "string") return nested;
        }
        return fallback;
    };

    async function handleOverride(id: string) {
        const reason = prompt("Override reason:");
        if (!reason) return;
        setResolving(id);
        try {
            await invoiceService.override(id, reason);
            toast.success("Exception resolved");
            setInvoices(prev => prev.filter(i => i.id !== id));
        } catch (error: unknown) {
            toast.error(getErrorMessage(error, "Failed"));
        } finally { setResolving(null); }
    }

    if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-accent" /></div>;

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Invoice Exceptions</h1>
                <p className="text-muted-foreground mt-1">{invoices.length} exception{invoices.length !== 1 && "s"} to resolve</p>
            </div>

            {invoices.length === 0 ? (
                <Card>
                    <CardContent className="py-12 text-center">
                        <CheckCircle className="mx-auto h-12 w-12 text-success mb-4 opacity-50" />
                        <h3 className="text-lg font-medium">No exceptions</h3>
                        <p className="text-muted-foreground mt-1">All invoices are matching properly</p>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-3">
                    {invoices.map((inv) => (
                        (() => {
                            const exceptions = inv.match_exceptions?.exceptions;
                            const issueCount = Array.isArray(exceptions) ? exceptions.length : 0;
                            return (
                        <Card key={inv.id} className="border-destructive/20">
                            <CardContent className="p-5 flex items-center justify-between gap-4">
                                <div className="flex items-center gap-4 flex-1">
                                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
                                        <AlertTriangle className="h-5 w-5" />
                                    </div>
                                    <div>
                                        <p className="font-medium font-mono">{inv.invoice_number}</p>
                                        <p className="text-sm text-muted-foreground">
                                            {formatCurrency(inv.total_cents)}
                                            {issueCount ? ` • ${issueCount} issue(s)` : ""}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <StatusBadge status="EXCEPTION" />
                                    <Button size="sm" onClick={() => handleOverride(inv.id)} disabled={resolving === inv.id}>
                                        {resolving === inv.id ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                                        Override
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                            );
                        })()
                    ))}
                </div>
            )}
        </div>
    );
}
