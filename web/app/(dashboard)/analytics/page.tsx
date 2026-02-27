"use client";

import { useEffect, useState } from "react";
import {
    BarChart,
    Bar,
    LineChart,
    Line,
    PieChart,
    Pie,
    Cell,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";
import { TrendingUp, Users, CheckCircle, Wallet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";
import { api } from "@/lib/api/client";
import { vendorService } from "@/lib/api/vendors";
import type { Vendor } from "@/types/models";

// ── Palette ────────────────────────────────────────────────────────────────
const PIE_COLORS = ["#4F46E5", "#22C55E", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#F97316"];

const STATUS_COLOR: Record<string, string> = {
    DRAFT: "#94A3B8",
    PENDING: "#F59E0B",
    APPROVED: "#22C55E",
    REJECTED: "#EF4444",
    CANCELLED: "#6B7280",
    UPLOADED: "#F59E0B",
    MATCHED: "#22C55E",
    EXCEPTION: "#EF4444",
    DISPUTED: "#F97316",
    PAID: "#8B5CF6",
    ACTIVE: "#22C55E",
    BLOCKED: "#EF4444",
    ARCHIVED: "#6B7280",
    PENDING_REVIEW: "#F59E0B",
};

// ── Helpers ────────────────────────────────────────────────────────────────
function groupBy<T>(items: T[], key: (item: T) => string): Record<string, T[]> {
    return items.reduce(
        (acc, item) => {
            const k = key(item);
            (acc[k] ??= []).push(item);
            return acc;
        },
        {} as Record<string, T[]>,
    );
}

// ── Custom Tooltips ────────────────────────────────────────────────────────
function CurrencyTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="rounded-lg border bg-background p-2 text-xs shadow-md">
            <p className="font-medium mb-1">{label}</p>
            {payload.map((p: any) => (
                <p key={p.dataKey} style={{ color: p.color }}>
                    {p.name}:{" "}
                    {p.value >= 100000
                        ? `₹${(p.value / 100000).toFixed(2)}L`
                        : `₹${p.value.toLocaleString("en-IN")}`}
                </p>
            ))}
        </div>
    );
}

function CountTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="rounded-lg border bg-background p-2 text-xs shadow-md">
            <p className="font-medium">
                {label}: <span className="text-accent">{payload[0]?.value}</span>
            </p>
        </div>
    );
}

// ── Types for analytics API ────────────────────────────────────────────────
interface SpendDept {
    department_id: string;
    department_name: string;
    total_budget_cents: number;
    spent_cents: number;
    reserved_cents: number;
    available_cents: number;
    utilization_pct: number;
}
interface SpendVendor {
    vendor_id: string;
    vendor_name: string;
    total_spent_cents: number;
    po_count: number;
}
interface MonthlyTrend {
    year: number;
    month: number;
    label: string;
    total_cents: number;
    invoice_count: number;
}
interface AnalyticsData {
    fiscal_year: number;
    quarter: number;
    summary: {
        total_budget_cents: number;
        total_spent_cents: number;
        total_reserved_cents: number;
        available_cents: number;
        budget_utilization_pct: number;
        total_po_spend_cents: number;
    };
    spend_by_department: SpendDept[];
    spend_by_vendor: SpendVendor[];
    pr_pipeline: Record<string, number>;
    monthly_invoice_trend: MonthlyTrend[];
}

// ── Page ───────────────────────────────────────────────────────────────────
export default function AnalyticsPage() {
    const [loading, setLoading] = useState(true);
    const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
    const [vendors, setVendors] = useState<Vendor[]>([]);

    useEffect(() => {
        Promise.allSettled([
            api.get("/analytics/spend").then((r: { data: AnalyticsData }) => r.data as AnalyticsData),
            vendorService.list({ limit: 25 }),
        ])
            .then(([a, v]) => {
                if (a.status === "fulfilled") setAnalytics(a.value);
                setVendors(v.status === "fulfilled" ? v.value.data : []);
            })
            .finally(() => setLoading(false));
    }, []);

    // ── Derived data from analytics API ─────────────────────────────────────
    const summary = analytics?.summary;
    const totalPOSpend = summary?.total_po_spend_cents ?? 0;
    const totalBudget = summary?.total_budget_cents ?? 0;
    const totalConsumed = summary?.total_spent_cents ?? 0;
    const budgetPct = summary?.budget_utilization_pct ?? 0;
    const activeVendors = vendors.filter((v) => v.status === "ACTIVE").length;

    // 1. Spend by Department (grouped bar — one row per department, pre-aggregated)
    const deptSpend = (analytics?.spend_by_department ?? []).map((d) => ({
        dept: d.department_name,
        Spent: Math.round(d.spent_cents / 100),
        Budget: Math.round(d.total_budget_cents / 100),
        utilization_pct: d.utilization_pct,
    }));

    // 2. PR Pipeline from analytics
    const prPipeline = analytics?.pr_pipeline ?? {};
    const prPipelineData = ["DRAFT", "PENDING", "APPROVED", "REJECTED", "CANCELLED"].map(
        (s) => ({
            status: s,
            count: prPipeline[s] ?? 0,
            fill: STATUS_COLOR[s] ?? "#94A3B8",
        }),
    );

    // 3. Top Vendors by PO value (from analytics)
    const vendorSpend = (analytics?.spend_by_vendor ?? []).slice(0, 5).map((v) => ({
        vendor:
            v.vendor_name.length > 22 ? v.vendor_name.slice(0, 22) + "…" : v.vendor_name,
        "PO Value": Math.round(v.total_spent_cents / 100),
    }));

    // 4. Vendor Status Pie
    const vendorStatusData = Object.entries(groupBy(vendors, (v) => v.status)).map(
        ([status, items]) => ({
            name: status.replace(/_/g, " "),
            value: items.length,
            key: status,
        }),
    );

    // 5. Monthly Invoice Spend (from analytics — already aggregated)
    const monthlyData = (analytics?.monthly_invoice_trend ?? []).map((m) => ({
        month: m.label,
        "Invoice Spend": Math.round(m.total_cents / 100),
        "Invoice Count": m.invoice_count,
    }));

    // 6. Invoice status breakdown from PR pipeline (approximate)
    const invoiceApproved = prPipeline["APPROVED"] ?? 0;
    const matchBreakdown = [
        { name: "Approved", value: invoiceApproved },
    ].filter((d) => d.value > 0);

    const matchColors: Record<string, string> = {
        Matched: "#22C55E",
        Exception: "#EF4444",
        Disputed: "#F97316",
        Uploaded: "#F59E0B",
        Paid: "#8B5CF6",
    };

    // ── Loading ──────────────────────────────────────────────────────────────
    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" />
            </div>
        );
    }

    // ── Render ───────────────────────────────────────────────────────────────
    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
                <p className="text-muted-foreground mt-1">
                    Procurement insights across your organization
                </p>
            </div>

            {/* ── KPI Strip ──────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                <KpiCard
                    label="Total PO Spend"
                    value={formatCurrency(totalPOSpend)}
                    sub="Across all active purchase orders"
                    icon={<TrendingUp className="h-5 w-5 text-accent" />}
                    iconBg="bg-accent/10"
                />
                <KpiCard
                    label={`FY${analytics?.fiscal_year ?? ""} Q${analytics?.quarter ?? ""}`}
                    value={`${budgetPct}%`}
                    sub="Current quarter budget utilization"
                    icon={<CheckCircle className="h-5 w-5 text-green-500" />}
                    iconBg="bg-green-500/10"
                />
                <KpiCard
                    label="Active Vendors"
                    value={String(activeVendors)}
                    sub={`of ${vendors.length} total vendors onboarded`}
                    icon={<Users className="h-5 w-5 text-blue-500" />}
                    iconBg="bg-blue-500/10"
                />
                <KpiCard
                    label="Budget Utilized"
                    value={`${budgetPct}%`}
                    sub={`${formatCurrency(totalConsumed)} of ${formatCurrency(totalBudget)}`}
                    icon={
                        <Wallet
                            className={`h-5 w-5 ${budgetPct >= 90 ? "text-red-500" : budgetPct >= 70 ? "text-amber-500" : "text-green-500"}`}
                        />
                    }
                    iconBg={
                        budgetPct >= 90
                            ? "bg-red-500/10"
                            : budgetPct >= 70
                                ? "bg-amber-500/10"
                                : "bg-green-500/10"
                    }
                />
            </div>

            {/* ── Spend by Department (grouped bar) + Budget Utilization ── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">
                            Department Spend vs Budget
                            <span className="text-xs font-normal text-muted-foreground ml-2">
                                (FY{analytics?.fiscal_year} Q{analytics?.quarter})
                            </span>
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {deptSpend.length > 0 ? (
                            <ResponsiveContainer width="100%" height={280}>
                                <BarChart data={deptSpend} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis dataKey="dept" tick={{ fontSize: 11 }} />
                                    <YAxis
                                        tick={{ fontSize: 11 }}
                                        tickFormatter={(v) =>
                                            v >= 100000
                                                ? `₹${(v / 100000).toFixed(1)}L`
                                                : `₹${(v / 1000).toFixed(0)}K`
                                        }
                                    />
                                    <Tooltip content={<CurrencyTooltip />} />
                                    <Legend wrapperStyle={{ fontSize: 11 }} />
                                    <Bar dataKey="Spent" fill="#4F46E5" radius={[4, 4, 0, 0]} />
                                    <Bar dataKey="Budget" fill="#E2E8F0" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <EmptyChart />
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">
                            Budget Utilization by Department
                            <span className="text-xs font-normal text-muted-foreground ml-2">
                                (FY{analytics?.fiscal_year} Q{analytics?.quarter})
                            </span>
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {deptSpend.length > 0 ? (
                            <div className="space-y-5 py-1">
                                {deptSpend.map((d) => {
                                    const pct = d.Budget > 0 ? Math.min(Math.round((d.Spent / d.Budget) * 100), 100) : 0;
                                    const color =
                                        pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-amber-500" : "bg-green-500";
                                    const textColor =
                                        pct >= 90 ? "text-red-500" : pct >= 70 ? "text-amber-500" : "text-green-600";
                                    return (
                                        <div key={d.dept}>
                                            <div className="flex justify-between text-xs mb-1.5">
                                                <span className="font-medium">{d.dept}</span>
                                                <span className={textColor + " font-semibold"}>
                                                    {pct}%
                                                </span>
                                            </div>
                                            <div className="h-2 rounded-full bg-muted overflow-hidden">
                                                <div
                                                    className={`h-full rounded-full transition-all ${color}`}
                                                    style={{ width: `${pct}%` }}
                                                />
                                            </div>
                                            <p className="text-xs text-muted-foreground mt-1">
                                                ₹{d.Spent.toLocaleString("en-IN")} spent of ₹{d.Budget.toLocaleString("en-IN")}
                                            </p>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <EmptyChart />
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* ── PR Pipeline + Top Vendors ──────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Purchase Request Pipeline</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={280}>
                            <BarChart
                                data={prPipelineData}
                                layout="vertical"
                                margin={{ top: 4, right: 24, left: 16, bottom: 0 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                                <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                                <YAxis
                                    type="category"
                                    dataKey="status"
                                    tick={{ fontSize: 11 }}
                                    width={80}
                                />
                                <Tooltip content={<CountTooltip />} />
                                <Bar dataKey="count" name="PRs" radius={[0, 4, 4, 0]}>
                                    {prPipelineData.map((entry) => (
                                        <Cell key={entry.status} fill={entry.fill} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            {/* ── Top Vendors  +  Vendor Status ───────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Top 5 Vendors by PO Value</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {vendorSpend.length > 0 ? (
                            <ResponsiveContainer width="100%" height={280}>
                                <BarChart
                                    data={vendorSpend}
                                    layout="vertical"
                                    margin={{ top: 4, right: 24, left: 8, bottom: 0 }}
                                >
                                    <CartesianGrid
                                        strokeDasharray="3 3"
                                        stroke="#f0f0f0"
                                        horizontal={false}
                                    />
                                    <XAxis
                                        type="number"
                                        tick={{ fontSize: 11 }}
                                        tickFormatter={(v) =>
                                            v >= 100000
                                                ? `₹${(v / 100000).toFixed(1)}L`
                                                : `₹${(v / 1000).toFixed(0)}K`
                                        }
                                    />
                                    <YAxis
                                        type="category"
                                        dataKey="vendor"
                                        tick={{ fontSize: 10 }}
                                        width={130}
                                    />
                                    <Tooltip content={<CurrencyTooltip />} />
                                    <Bar dataKey="PO Value" fill="#06B6D4" radius={[0, 4, 4, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <EmptyChart label="No purchase order data yet" />
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Vendor Onboarding Status</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {vendorStatusData.length > 0 ? (
                            <ResponsiveContainer width="100%" height={280}>
                                <PieChart>
                                    <Pie
                                        data={vendorStatusData}
                                        cx="50%"
                                        cy="50%"
                                        outerRadius={105}
                                        paddingAngle={3}
                                        dataKey="value"
                                        label={({ name, percent }) =>
                                            (percent ?? 0) > 0.05
                                                ? `${name} ${Math.round((percent ?? 0) * 100)}%`
                                                : ""
                                        }
                                        labelLine={false}
                                    >
                                        {vendorStatusData.map((entry, i) => (
                                            <Cell
                                                key={entry.key}
                                                fill={
                                                    STATUS_COLOR[entry.key] ??
                                                    PIE_COLORS[i % PIE_COLORS.length]
                                                }
                                            />
                                        ))}
                                    </Pie>
                                    <Tooltip
                                        formatter={(v: number | undefined, name: string | undefined) => [
                                            `${v ?? 0} vendor${(v ?? 0) !== 1 ? "s" : ""}`,
                                            name ?? "",
                                        ]}
                                    />
                                    <Legend wrapperStyle={{ fontSize: 11 }} />
                                </PieChart>
                            </ResponsiveContainer>
                        ) : (
                            <EmptyChart label="No vendor data" />
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* ── Monthly Invoice Volume (full width) ─────────────────────── */}
            {monthlyData.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Monthly Invoice Spend Trend</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={280}>
                            <LineChart
                                data={monthlyData}
                                margin={{ top: 4, right: 24, left: 0, bottom: 0 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                                <YAxis
                                    tick={{ fontSize: 11 }}
                                    tickFormatter={(v) =>
                                        v >= 100000
                                            ? `₹${(v / 100000).toFixed(1)}L`
                                            : `₹${(v / 1000).toFixed(0)}K`
                                    }
                                />
                                <Tooltip content={<CurrencyTooltip />} />
                                <Line
                                    type="monotone"
                                    dataKey="Invoice Spend"
                                    stroke="#4F46E5"
                                    strokeWidth={2.5}
                                    dot={{ fill: "#4F46E5", strokeWidth: 0, r: 4 }}
                                    activeDot={{ r: 6, strokeWidth: 0 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function KpiCard({
    label,
    value,
    sub,
    icon,
    iconBg,
}: {
    label: string;
    value: string;
    sub: string;
    icon: React.ReactNode;
    iconBg: string;
}) {
    return (
        <Card>
            <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-sm text-muted-foreground">{label}</p>
                        <p className="text-2xl font-bold font-mono mt-1">{value}</p>
                        <p className="text-xs text-muted-foreground mt-1">{sub}</p>
                    </div>
                    <div className={`rounded-full p-2.5 ${iconBg}`}>{icon}</div>
                </div>
            </CardContent>
        </Card>
    );
}

function EmptyChart({ label = "No data available" }: { label?: string }) {
    return (
        <div className="flex h-[280px] items-center justify-center">
            <p className="text-sm text-muted-foreground">{label}</p>
        </div>
    );
}
