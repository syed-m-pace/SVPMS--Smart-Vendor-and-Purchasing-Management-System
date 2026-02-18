"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
    FileText, ShoppingCart, Package, AlertTriangle,
    TrendingUp, ArrowUpRight, Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { api } from "@/lib/api/client";
import { formatCurrency, formatDate, timeAgo } from "@/lib/utils";
import type { PurchaseRequest } from "@/types/models";

interface StatsData {
    pending_prs: number;
    active_pos: number;
    invoice_exceptions: number;
    budget_utilization: number;
}

export default function DashboardPage() {
    const [stats, setStats] = useState<StatsData | null>(null);
    const [recentPRs, setRecentPRs] = useState<PurchaseRequest[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function load() {
            try {
                // Fetch dashboard data in parallel
                const [prRes, budgetRes] = await Promise.all([
                    api.get("/purchase-requests", { params: { per_page: 5 } }),
                    api.get("/budgets", { params: { fiscal_year: 2026, quarter: 1 } }), // Fetch Q1 2026 budgets
                ]);

                const prData = prRes.data;
                const prs = prData.data || prData;
                setRecentPRs(Array.isArray(prs) ? prs : []);

                // Calculate stats from available data
                const pendingPRs = Array.isArray(prs)
                    ? prs.filter((p: any) => p.status === "PENDING").length
                    : 0;

                const budgets = budgetRes.data.data || [];
                const totalBudget = budgets.reduce((sum: number, b: any) => sum + b.total_cents, 0);
                const totalSpent = budgets.reduce((sum: number, b: any) => sum + (b.spent_cents || 0), 0);
                const utilization = totalBudget > 0 ? Math.round((totalSpent / totalBudget) * 100) : 0;

                setStats({
                    pending_prs: pendingPRs,
                    active_pos: 0,
                    invoice_exceptions: 0,
                    budget_utilization: utilization,
                });
            } catch (err) {
                console.error("Dashboard load failed:", err);
                setStats({ pending_prs: 0, active_pos: 0, invoice_exceptions: 0, budget_utilization: 0 });
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    if (loading) {
        return (
            <div className="flex h-[60vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-accent" />
            </div>
        );
    }

    const kpiCards = [
        {
            title: "Pending PRs",
            value: stats?.pending_prs ?? 0,
            icon: FileText,
            href: "/purchase-requests?status=PENDING",
            color: "text-sky-500",
            bg: "bg-sky-500/10",
        },
        {
            title: "Active POs",
            value: stats?.active_pos ?? 0,
            icon: ShoppingCart,
            href: "/purchase-orders",
            color: "text-emerald-500",
            bg: "bg-emerald-500/10",
        },
        {
            title: "Invoice Exceptions",
            value: stats?.invoice_exceptions ?? 0,
            icon: AlertTriangle,
            href: "/exceptions",
            color: "text-red-500",
            bg: "bg-red-500/10",
            alert: (stats?.invoice_exceptions ?? 0) > 0,
        },
        {
            title: "Budget Utilization",
            value: `${stats?.budget_utilization ?? 0}%`,
            icon: TrendingUp,
            href: "/budgets",
            color: "text-violet-500",
            bg: "bg-violet-500/10",
        },
    ];

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                <p className="text-muted-foreground mt-1">
                    Overview of your procurement activity
                </p>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {kpiCards.map((kpi) => (
                    <Link key={kpi.title} href={kpi.href}>
                        <Card
                            className={`group hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 ${kpi.alert ? "ring-2 ring-destructive/20" : ""
                                }`}
                        >
                            <CardContent className="p-6">
                                <div className="flex items-center justify-between">
                                    <div className={`rounded-lg p-2.5 ${kpi.bg}`}>
                                        <kpi.icon className={`h-5 w-5 ${kpi.color}`} />
                                    </div>
                                    <ArrowUpRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                                </div>
                                <div className="mt-4">
                                    <p className="text-3xl font-bold font-mono">{kpi.value}</p>
                                    <p className="text-sm text-muted-foreground mt-1">
                                        {kpi.title}
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                ))}
            </div>

            {/* Recent Purchase Requests */}
            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-lg">Recent Purchase Requests</CardTitle>
                    <Button variant="outline" size="sm" asChild>
                        <Link href="/purchase-requests">View All</Link>
                    </Button>
                </CardHeader>
                <CardContent>
                    {recentPRs.length === 0 ? (
                        <div className="py-8 text-center text-muted-foreground">
                            <FileText className="mx-auto h-10 w-10 mb-3 opacity-30" />
                            <p>No purchase requests yet</p>
                            <Button variant="outline" size="sm" className="mt-4" asChild>
                                <Link href="/purchase-requests/new">Create First PR</Link>
                            </Button>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {recentPRs.map((pr) => (
                                <Link
                                    key={pr.id}
                                    href={`/purchase-requests/${pr.id}`}
                                    className="flex items-center justify-between rounded-lg border p-4 hover:bg-muted/30 transition-colors"
                                >
                                    <div className="flex items-center gap-4">
                                        <div>
                                            <p className="font-medium font-mono text-sm">
                                                {pr.pr_number}
                                            </p>
                                            <p className="text-sm text-muted-foreground truncate max-w-[300px]">
                                                {pr.description || "No description"}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <StatusBadge status={pr.status} />
                                        <span className="text-sm font-mono font-medium">
                                            {formatCurrency(pr.total_cents)}
                                        </span>
                                        <span className="text-xs text-muted-foreground">
                                            {timeAgo(pr.created_at)}
                                        </span>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
