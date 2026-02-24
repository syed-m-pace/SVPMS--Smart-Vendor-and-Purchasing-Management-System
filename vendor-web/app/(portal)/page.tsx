"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShoppingCart, Gavel, Receipt, AlertTriangle, ArrowRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { dashboardService } from "@/lib/api/dashboard";
import { vendorService } from "@/lib/api/vendor";
import { useAuthStore } from "@/lib/stores/auth";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { DashboardStats, PurchaseOrder, VendorScorecard } from "@/types/models";

function StatCard({
    label,
    value,
    icon: Icon,
    href,
    color,
}: {
    label: string;
    value: number;
    icon: React.ElementType;
    href: string;
    color: string;
}) {
    return (
        <Link href={href}>
            <Card className="p-5 hover:shadow-md transition-shadow cursor-pointer">
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-sm text-muted-foreground">{label}</p>
                        <p className="text-3xl font-bold mt-1">{value}</p>
                    </div>
                    <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${color}`}>
                        <Icon className="h-6 w-6 text-white" />
                    </div>
                </div>
            </Card>
        </Link>
    );
}

function ScorecardMini({ scorecard }: { scorecard: VendorScorecard }) {
    const items = [
        { label: "On-time Delivery", value: scorecard.on_time_delivery_pct },
        { label: "Invoice Acceptance", value: scorecard.invoice_acceptance_pct },
        { label: "Fulfillment Rate", value: scorecard.fulfillment_rate_pct },
        { label: "RFQ Response", value: scorecard.rfq_response_pct },
    ];
    return (
        <Card className="p-5">
            <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Your Scorecard</h3>
                <Link href="/analytics">
                    <Button variant="ghost" size="sm">
                        View Details <ArrowRight className="h-3 w-3 ml-1" />
                    </Button>
                </Link>
            </div>
            <div className="grid grid-cols-2 gap-4">
                {items.map((item) => (
                    <div key={item.label}>
                        <p className="text-xs text-muted-foreground">{item.label}</p>
                        <p className="text-lg font-bold">{item.value.toFixed(0)}%</p>
                        <div className="h-1.5 bg-muted rounded-full mt-1">
                            <div
                                className="h-full bg-accent rounded-full transition-all"
                                style={{ width: `${Math.min(item.value, 100)}%` }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </Card>
    );
}

export default function DashboardPage() {
    const vendor = useAuthStore((s) => s.vendor);
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [recentPOs, setRecentPOs] = useState<PurchaseOrder[]>([]);
    const [scorecard, setScorecard] = useState<VendorScorecard | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            dashboardService.getStats().catch(() => null),
            dashboardService.getRecentPOs().catch(() => null),
            vendor ? vendorService.getScorecard(vendor.id).catch(() => null) : null,
        ]).then(([s, po, sc]) => {
            if (s) setStats(s);
            if (po) setRecentPOs(po.data);
            if (sc) setScorecard(sc);
            setLoading(false);
        });
    }, [vendor]);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Dashboard</h1>
                <p className="text-muted-foreground">
                    Welcome back{vendor ? `, ${vendor.legal_name}` : ""}
                </p>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    label="Active POs"
                    value={stats?.active_pos ?? 0}
                    icon={ShoppingCart}
                    href="/purchase-orders"
                    color="bg-accent"
                />
                <StatCard
                    label="Pending RFQs"
                    value={stats?.pending_rfqs ?? 0}
                    icon={Gavel}
                    href="/rfqs"
                    color="bg-info"
                />
                <StatCard
                    label="Open Invoices"
                    value={stats?.open_invoices ?? 0}
                    icon={Receipt}
                    href="/invoices"
                    color="bg-success"
                />
                <StatCard
                    label="Invoice Exceptions"
                    value={stats?.invoice_exceptions ?? 0}
                    icon={AlertTriangle}
                    href="/invoices?status=EXCEPTION"
                    color="bg-destructive"
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Recent POs */}
                <Card className="p-5">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold">Recent Purchase Orders</h3>
                        <Link href="/purchase-orders">
                            <Button variant="ghost" size="sm">
                                View All <ArrowRight className="h-3 w-3 ml-1" />
                            </Button>
                        </Link>
                    </div>
                    {recentPOs.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-4 text-center">No purchase orders yet</p>
                    ) : (
                        <div className="space-y-3">
                            {recentPOs.slice(0, 5).map((po) => (
                                <Link
                                    key={po.id}
                                    href={`/purchase-orders/${po.id}`}
                                    className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 transition-colors"
                                >
                                    <div>
                                        <p className="text-sm font-medium">{po.po_number}</p>
                                        <p className="text-xs text-muted-foreground">{formatDate(po.created_at)}</p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span className="text-sm font-medium">{formatCurrency(po.total_cents, po.currency)}</span>
                                        <StatusBadge status={po.status} />
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )}
                </Card>

                {/* Scorecard */}
                {scorecard ? (
                    <ScorecardMini scorecard={scorecard} />
                ) : (
                    <Card className="p-5 flex items-center justify-center">
                        <p className="text-sm text-muted-foreground">Scorecard not available yet</p>
                    </Card>
                )}
            </div>
        </div>
    );
}
