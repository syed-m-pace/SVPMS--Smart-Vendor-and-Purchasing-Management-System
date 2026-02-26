"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
    FileText, ShoppingCart, Package, AlertTriangle,
    TrendingUp, ArrowUpRight, Loader2, Users, Receipt,
    DollarSign, BarChart3, PieChart as PieChartIcon,
    ArrowUp, ArrowDown, Clock, CheckCircle2, XCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { api } from "@/lib/api/client";
import { formatCurrency, formatDate, timeAgo } from "@/lib/utils";
import type { PurchaseRequest } from "@/types/models";
import {
    PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
    CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

interface StatsData {
    pending_prs: number;
    active_pos: number;
    invoice_exceptions: number;
    budget_utilization: number;
    open_invoices: number;
    pending_rfqs: number;
    total_vendors: number;
    total_invoices: number;
    total_po_value_cents: number;
    total_budget_cents: number;
    total_spent_cents: number;
    invoice_status_breakdown: Record<string, number>;
    payment_chart: Array<{ name: string; value: number; color: string }>;
}

interface AnalyticsData {
    spend_by_department: Array<{
        department_name: string;
        total_budget_cents: number;
        spent_cents: number;
        utilization_pct: number;
    }>;
    spend_by_vendor: Array<{
        vendor_name: string;
        total_spent_cents: number;
        po_count: number;
    }>;
    pr_pipeline: Record<string, number>;
    monthly_invoice_trend: Array<{
        label: string;
        total_cents: number;
        invoice_count: number;
    }>;
}

const CHART_COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

const CustomTooltipContent = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="rounded-lg border bg-background/95 backdrop-blur-sm p-3 shadow-xl">
                <p className="text-sm font-medium text-foreground mb-1">{label}</p>
                {payload.map((p: any, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: p.color }} />
                        <span className="text-muted-foreground">{p.name}:</span>
                        <span className="font-mono font-medium">{typeof p.value === 'number' && p.value > 1000 ? formatCurrency(p.value) : p.value}</span>
                    </div>
                ))}
            </div>
        );
    }
    return null;
};

export default function DashboardPage() {
    const [stats, setStats] = useState<StatsData | null>(null);
    const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
    const [recentPRs, setRecentPRs] = useState<PurchaseRequest[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function load() {
            try {
                const [statsRes, prRes, analyticsRes] = await Promise.all([
                    api.get("/dashboard/stats"),
                    api.get("/purchase-requests", { params: { limit: 5 } }),
                    api.get("/analytics/spend").catch(() => null),
                ]);

                const prData = prRes.data;
                const prs = prData.data || prData;
                setRecentPRs(Array.isArray(prs) ? prs : []);
                setStats(statsRes.data);
                if (analyticsRes?.data) setAnalytics(analyticsRes.data);
            } catch (err) {
                console.error("Dashboard load failed:", err);
                setStats({
                    pending_prs: 0, active_pos: 0, invoice_exceptions: 0,
                    budget_utilization: 0, open_invoices: 0, pending_rfqs: 0,
                    total_vendors: 0, total_invoices: 0, total_po_value_cents: 0,
                    total_budget_cents: 0, total_spent_cents: 0,
                    invoice_status_breakdown: {}, payment_chart: [],
                });
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

    /* ========== KPI Cards ========== */
    const kpiCards = [
        {
            title: "Pending PRs",
            value: stats?.pending_prs ?? 0,
            icon: FileText,
            href: "/purchase-requests?status=PENDING",
            gradient: "from-sky-500/15 to-sky-500/5",
            iconBg: "bg-sky-500/15",
            iconColor: "text-sky-500",
        },
        {
            title: "Active POs",
            value: stats?.active_pos ?? 0,
            icon: ShoppingCart,
            href: "/purchase-orders",
            gradient: "from-emerald-500/15 to-emerald-500/5",
            iconBg: "bg-emerald-500/15",
            iconColor: "text-emerald-500",
        },
        {
            title: "Invoice Exceptions",
            value: stats?.invoice_exceptions ?? 0,
            icon: AlertTriangle,
            href: "/exceptions",
            gradient: "from-red-500/15 to-red-500/5",
            iconBg: "bg-red-500/15",
            iconColor: "text-red-500",
            alert: (stats?.invoice_exceptions ?? 0) > 0,
        },
        {
            title: "Budget Utilization",
            value: `${stats?.budget_utilization ?? 0}%`,
            icon: TrendingUp,
            href: "/budgets",
            gradient: "from-violet-500/15 to-violet-500/5",
            iconBg: "bg-violet-500/15",
            iconColor: "text-violet-500",
        },
        {
            title: "Total Vendors",
            value: stats?.total_vendors ?? 0,
            icon: Users,
            href: "/vendors",
            gradient: "from-orange-500/15 to-orange-500/5",
            iconBg: "bg-orange-500/15",
            iconColor: "text-orange-500",
        },
        {
            title: "Total Invoices",
            value: stats?.total_invoices ?? 0,
            icon: Receipt,
            href: "/invoices",
            gradient: "from-cyan-500/15 to-cyan-500/5",
            iconBg: "bg-cyan-500/15",
            iconColor: "text-cyan-500",
        },
    ];

    /* ========== Financial summary ========== */
    const totalBudget = stats?.total_budget_cents ?? 0;
    const totalSpent = stats?.total_spent_cents ?? 0;
    const totalPOValue = stats?.total_po_value_cents ?? 0;

    /* ========== PR pipeline data for bar chart ========== */
    const prPipelineData = analytics?.pr_pipeline
        ? Object.entries(analytics.pr_pipeline).map(([status, count]) => ({
            status: status.replace(/_/g, " "),
            count,
        }))
        : [];

    /* ========== Spend by department for bar chart ========== */
    const deptSpendData = analytics?.spend_by_department?.map(d => ({
        name: d.department_name.length > 12
            ? d.department_name.slice(0, 12) + "…"
            : d.department_name,
        budget: d.total_budget_cents / 100,
        spent: d.spent_cents / 100,
    })) || [];

    /* ========== Monthly invoice trend ========== */
    const monthlyTrend = analytics?.monthly_invoice_trend?.map(m => ({
        label: m.label,
        amount: m.total_cents / 100,
        count: m.invoice_count,
    })) || [];

    /* ========== Payment chart data ========== */
    const paymentData = stats?.payment_chart?.filter(d => d.value > 0) ?? [];
    const totalPayments = paymentData.reduce((acc, d) => acc + d.value, 0);

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                <p className="text-muted-foreground mt-1">
                    Overview of your procurement activity
                </p>
            </div>

            {/* ──── KPI Cards ──── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
                {kpiCards.map((kpi) => (
                    <Link key={kpi.title} href={kpi.href}>
                        <Card
                            className={`group relative overflow-hidden hover:shadow-lg transition-all duration-300 hover:-translate-y-1 ${kpi.alert ? "ring-2 ring-destructive/30" : ""}`}
                        >
                            <div className={`absolute inset-0 bg-gradient-to-br ${kpi.gradient} opacity-60`} />
                            <CardContent className="relative p-5">
                                <div className="flex items-center justify-between">
                                    <div className={`rounded-xl p-2.5 ${kpi.iconBg}`}>
                                        <kpi.icon className={`h-5 w-5 ${kpi.iconColor}`} />
                                    </div>
                                    <ArrowUpRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-all duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                                </div>
                                <div className="mt-3">
                                    <p className="text-2xl font-bold font-mono">{kpi.value}</p>
                                    <p className="text-xs text-muted-foreground mt-1 uppercase tracking-wider font-medium">
                                        {kpi.title}
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                ))}
            </div>

            {/* ──── Financial Summary Row ──── */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="border-l-4 border-l-blue-500">
                    <CardContent className="p-5">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium">Total Budget</p>
                                <p className="text-2xl font-bold font-mono mt-1">{formatCurrency(totalBudget)}</p>
                            </div>
                            <div className="rounded-xl bg-blue-500/10 p-3">
                                <DollarSign className="h-6 w-6 text-blue-500" />
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-4 border-l-emerald-500">
                    <CardContent className="p-5">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium">Total Spent</p>
                                <p className="text-2xl font-bold font-mono mt-1">{formatCurrency(totalSpent)}</p>
                            </div>
                            <div className="rounded-xl bg-emerald-500/10 p-3">
                                <ArrowUp className="h-6 w-6 text-emerald-500" />
                            </div>
                        </div>
                        {totalBudget > 0 && (
                            <div className="mt-3">
                                <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                                    <span>of budget</span>
                                    <span className="font-mono">{Math.round((totalSpent / totalBudget) * 100)}%</span>
                                </div>
                                <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all duration-700"
                                        style={{ width: `${Math.min((totalSpent / totalBudget) * 100, 100)}%` }}
                                    />
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
                <Card className="border-l-4 border-l-violet-500">
                    <CardContent className="p-5">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium">Total PO Value</p>
                                <p className="text-2xl font-bold font-mono mt-1">{formatCurrency(totalPOValue)}</p>
                            </div>
                            <div className="rounded-xl bg-violet-500/10 p-3">
                                <Package className="h-6 w-6 text-violet-500" />
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* ──── Charts Row ──── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Payment Status Chart (Donut) */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <div className="flex items-center gap-2">
                            <PieChartIcon className="h-5 w-5 text-muted-foreground" />
                            <CardTitle className="text-lg">Payment Status</CardTitle>
                        </div>
                        <Button variant="outline" size="sm" asChild>
                            <Link href="/invoices">View Invoices</Link>
                        </Button>
                    </CardHeader>
                    <CardContent>
                        {totalPayments === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                                <PieChartIcon className="h-12 w-12 mb-3 opacity-20" />
                                <p className="text-sm">No invoice data yet</p>
                            </div>
                        ) : (
                            <div className="flex items-center gap-6">
                                <ResponsiveContainer width="50%" height={220}>
                                    <PieChart>
                                        <Pie
                                            data={paymentData}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={55}
                                            outerRadius={85}
                                            paddingAngle={4}
                                            dataKey="value"
                                            strokeWidth={0}
                                        >
                                            {paymentData.map((entry, i) => (
                                                <Cell key={i} fill={entry.color} />
                                            ))}
                                        </Pie>
                                        <Tooltip content={<CustomTooltipContent />} />
                                    </PieChart>
                                </ResponsiveContainer>
                                <div className="flex-1 space-y-4">
                                    {paymentData.map((d) => (
                                        <div key={d.name} className="flex items-center gap-3">
                                            <div className="flex items-center gap-2 flex-1">
                                                <span
                                                    className="h-3 w-3 rounded-full shrink-0"
                                                    style={{ backgroundColor: d.color }}
                                                />
                                                <span className="text-sm font-medium">{d.name}</span>
                                            </div>
                                            <span className="text-lg font-bold font-mono">{d.value}</span>
                                            <span className="text-xs text-muted-foreground w-10 text-right">
                                                {Math.round((d.value / totalPayments) * 100)}%
                                            </span>
                                        </div>
                                    ))}
                                    <div className="border-t pt-3 flex items-center justify-between">
                                        <span className="text-sm text-muted-foreground">Total</span>
                                        <span className="text-lg font-bold font-mono">{totalPayments}</span>
                                    </div>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* PR Pipeline Bar Chart */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <div className="flex items-center gap-2">
                            <BarChart3 className="h-5 w-5 text-muted-foreground" />
                            <CardTitle className="text-lg">PR Pipeline</CardTitle>
                        </div>
                        <Button variant="outline" size="sm" asChild>
                            <Link href="/purchase-requests">View All</Link>
                        </Button>
                    </CardHeader>
                    <CardContent>
                        {prPipelineData.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                                <BarChart3 className="h-12 w-12 mb-3 opacity-20" />
                                <p className="text-sm">No PR data available</p>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height={220}>
                                <BarChart data={prPipelineData} barCategoryGap="20%">
                                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                                    <XAxis dataKey="status" tick={{ fontSize: 11 }} className="text-muted-foreground" />
                                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                                    <Tooltip content={<CustomTooltipContent />} />
                                    <Bar dataKey="count" name="Count" radius={[6, 6, 0, 0]} maxBarSize={40}>
                                        {prPipelineData.map((_, i) => (
                                            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* ──── Second Charts Row ──── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Monthly Invoice Trend */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <div className="flex items-center gap-2">
                            <TrendingUp className="h-5 w-5 text-muted-foreground" />
                            <CardTitle className="text-lg">Monthly Invoice Trend</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {monthlyTrend.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                                <TrendingUp className="h-12 w-12 mb-3 opacity-20" />
                                <p className="text-sm">No trend data yet</p>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height={220}>
                                <BarChart data={monthlyTrend} barCategoryGap="25%">
                                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                                    <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                                    <Tooltip
                                        content={({ active, payload, label }) => {
                                            if (active && payload?.length) {
                                                return (
                                                    <div className="rounded-lg border bg-background/95 backdrop-blur-sm p-3 shadow-xl">
                                                        <p className="text-sm font-medium mb-1">{label}</p>
                                                        <p className="text-sm text-muted-foreground">Amount: <span className="font-mono font-medium text-foreground">₹{Number(payload[0].value).toLocaleString("en-IN")}</span></p>
                                                        <p className="text-sm text-muted-foreground">Invoices: <span className="font-mono font-medium text-foreground">{payload[1]?.value ?? 0}</span></p>
                                                    </div>
                                                );
                                            }
                                            return null;
                                        }}
                                    />
                                    <Bar dataKey="amount" name="Amount" fill="#3b82f6" radius={[6, 6, 0, 0]} maxBarSize={40} />
                                    <Bar dataKey="count" name="Count" fill="#8b5cf6" radius={[6, 6, 0, 0]} maxBarSize={40} />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </CardContent>
                </Card>

                {/* Department Spend */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <div className="flex items-center gap-2">
                            <DollarSign className="h-5 w-5 text-muted-foreground" />
                            <CardTitle className="text-lg">Department Spend</CardTitle>
                        </div>
                        <Button variant="outline" size="sm" asChild>
                            <Link href="/budgets">View Budgets</Link>
                        </Button>
                    </CardHeader>
                    <CardContent>
                        {deptSpendData.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                                <DollarSign className="h-12 w-12 mb-3 opacity-20" />
                                <p className="text-sm">No department data yet</p>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height={220}>
                                <BarChart data={deptSpendData} barCategoryGap="20%">
                                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                                    <Tooltip content={<CustomTooltipContent />} />
                                    <Legend wrapperStyle={{ fontSize: "12px" }} />
                                    <Bar dataKey="budget" name="Budget" fill="#3b82f6" radius={[4, 4, 0, 0]} maxBarSize={30} />
                                    <Bar dataKey="spent" name="Spent" fill="#22c55e" radius={[4, 4, 0, 0]} maxBarSize={30} />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* ──── Invoice Breakdown Detail + Top Vendors ──── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Invoice Status Breakdown */}
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Receipt className="h-5 w-5 text-muted-foreground" />
                            <CardTitle className="text-lg">Invoice Status Breakdown</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {Object.keys(stats?.invoice_status_breakdown ?? {}).length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                                <Receipt className="h-10 w-10 mb-3 opacity-20" />
                                <p className="text-sm">No invoices recorded yet</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {Object.entries(stats!.invoice_status_breakdown).map(([status, count]) => {
                                    const total = Object.values(stats!.invoice_status_breakdown).reduce((a, b) => a + b, 0);
                                    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                                    const statusColor: Record<string, string> = {
                                        UPLOADED: "#f59e0b",
                                        PROCESSING: "#eab308",
                                        MATCHED: "#3b82f6",
                                        EXCEPTION: "#ef4444",
                                        DISPUTED: "#f97316",
                                        APPROVED: "#22c55e",
                                        APPROVED_FOR_PAYMENT: "#16a34a",
                                        PAID: "#10b981",
                                    };
                                    return (
                                        <div key={status} className="group">
                                            <div className="flex items-center justify-between mb-1.5">
                                                <div className="flex items-center gap-2">
                                                    <span
                                                        className="h-2.5 w-2.5 rounded-full"
                                                        style={{ backgroundColor: statusColor[status] ?? "#6b7280" }}
                                                    />
                                                    <span className="text-sm font-medium">{status.replace(/_/g, " ")}</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm font-bold font-mono">{count}</span>
                                                    <span className="text-xs text-muted-foreground w-8 text-right">{pct}%</span>
                                                </div>
                                            </div>
                                            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                                                <div
                                                    className="h-full rounded-full transition-all duration-500"
                                                    style={{
                                                        width: `${pct}%`,
                                                        backgroundColor: statusColor[status] ?? "#6b7280",
                                                    }}
                                                />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Top Vendors by Spend */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Users className="h-5 w-5 text-muted-foreground" />
                            <CardTitle className="text-lg">Top Vendors by Spend</CardTitle>
                        </div>
                        <Button variant="outline" size="sm" asChild>
                            <Link href="/vendors">View All</Link>
                        </Button>
                    </CardHeader>
                    <CardContent>
                        {(!analytics?.spend_by_vendor || analytics.spend_by_vendor.length === 0) ? (
                            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                                <Users className="h-10 w-10 mb-3 opacity-20" />
                                <p className="text-sm">No vendor spend data yet</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {analytics.spend_by_vendor.slice(0, 5).map((v, i) => (
                                    <div key={v.vendor_name} className="flex items-center gap-3 rounded-lg border p-3 hover:bg-muted/30 transition-colors">
                                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/10 text-accent text-sm font-bold">
                                            {i + 1}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium truncate">{v.vendor_name}</p>
                                            <p className="text-xs text-muted-foreground">{v.po_count} POs</p>
                                        </div>
                                        <span className="text-sm font-bold font-mono">{formatCurrency(v.total_spent_cents)}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* ──── Recent Purchase Requests ──── */}
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
