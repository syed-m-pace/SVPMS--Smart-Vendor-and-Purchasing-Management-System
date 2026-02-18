"use client";

import { useEffect, useState } from "react";
import { Wallet, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { budgetService } from "@/lib/api/services";
import { formatCurrency } from "@/lib/utils";
import type { Budget } from "@/types/models";

export default function BudgetsPage() {
    const [budgets, setBudgets] = useState<Budget[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        budgetService.list().then((r) => setBudgets(r.data)).catch(() => { }).finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-accent" /></div>;

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Budget Overview</h1>
                <p className="text-muted-foreground mt-1">Department budget allocation and utilization</p>
            </div>

            {budgets.length === 0 ? (
                <Card>
                    <CardContent className="py-12 text-center">
                        <Wallet className="mx-auto h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                        <h3 className="text-lg font-medium">No budgets found</h3>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {budgets.map((b) => {
                        const used = (b.spent_cents || 0) + (b.reserved_cents || 0);
                        const utilization = b.total_cents > 0 ? Math.round((used / b.total_cents) * 100) : 0;
                        const barColor = utilization > 90 ? "bg-destructive" : utilization > 70 ? "bg-warning" : "bg-success";
                        return (
                            <Card key={b.id}>
                                <CardHeader className="pb-3">
                                    <div className="flex items-center justify-between">
                                        <CardTitle className="text-base">{b.department?.name || "Department"}</CardTitle>
                                        <span className="text-xs font-mono text-muted-foreground">FY{b.fiscal_year} Q{b.quarter}</span>
                                    </div>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex justify-between text-sm">
                                        <span className="text-muted-foreground">Total Budget</span>
                                        <span className="font-mono font-medium">{formatCurrency(b.total_cents)}</span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-muted-foreground">Spent</span>
                                        <span className="font-mono">{formatCurrency(b.spent_cents)}</span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-muted-foreground">Reserved</span>
                                        <span className="font-mono">{formatCurrency(b.reserved_cents)}</span>
                                    </div>
                                    {/* Utilization bar */}
                                    <div>
                                        <div className="flex justify-between text-xs mb-1">
                                            <span className="text-muted-foreground">Utilization</span>
                                            <span className="font-medium">{utilization}%</span>
                                        </div>
                                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                                            <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${Math.min(utilization, 100)}%` }} />
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
