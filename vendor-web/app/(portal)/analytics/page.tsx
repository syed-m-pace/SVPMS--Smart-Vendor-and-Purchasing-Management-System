"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { useAuthStore } from "@/lib/stores/auth";
import { vendorService } from "@/lib/api/vendor";
import { analyticsService, type SpendAnalytics } from "@/lib/api/analytics";
import { formatCurrency } from "@/lib/utils";
import type { VendorScorecard } from "@/types/models";

function ScoreGauge({ label, value, color }: { label: string; value: number; color: string }) {
    return (
        <div className="text-center">
            <div className="relative inline-flex items-center justify-center w-24 h-24">
                <svg className="w-24 h-24 -rotate-90" viewBox="0 0 36 36">
                    <circle cx="18" cy="18" r="15.9155" fill="none" stroke="hsl(var(--muted))" strokeWidth="3" />
                    <circle
                        cx="18" cy="18" r="15.9155" fill="none"
                        stroke={color}
                        strokeWidth="3"
                        strokeDasharray={`${value} ${100 - value}`}
                        strokeLinecap="round"
                    />
                </svg>
                <span className="absolute text-lg font-bold">{value.toFixed(0)}%</span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">{label}</p>
        </div>
    );
}

export default function AnalyticsPage() {
    const vendor = useAuthStore((s) => s.vendor);
    const [scorecard, setScorecard] = useState<VendorScorecard | null>(null);
    const [spend, setSpend] = useState<SpendAnalytics | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            vendor ? vendorService.getScorecard(vendor.id).catch(() => null) : null,
            analyticsService.getSpend().catch(() => null),
        ]).then(([sc, sp]) => {
            if (sc) setScorecard(sc);
            if (sp) setSpend(sp);
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
                <h1 className="text-2xl font-bold">Analytics</h1>
                <p className="text-muted-foreground">Your performance metrics and spend overview</p>
            </div>

            {/* Vendor Scorecard */}
            {scorecard && (
                <Card className="p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-lg font-semibold">Performance Scorecard</h3>
                        <div className="text-right">
                            <p className="text-sm text-muted-foreground">Overall Score</p>
                            <p className="text-3xl font-bold text-accent">{scorecard.overall_score.toFixed(0)}</p>
                        </div>
                    </div>
                    <div className="flex flex-wrap justify-center gap-8">
                        <ScoreGauge label="On-Time Delivery" value={scorecard.on_time_delivery_pct} color="hsl(var(--success))" />
                        <ScoreGauge label="Invoice Acceptance" value={scorecard.invoice_acceptance_pct} color="hsl(var(--accent))" />
                        <ScoreGauge label="Fulfillment Rate" value={scorecard.fulfillment_rate_pct} color="hsl(var(--info))" />
                        <ScoreGauge label="RFQ Response" value={scorecard.rfq_response_pct} color="hsl(var(--warning))" />
                    </div>
                    <div className="mt-6 pt-4 border-t text-center">
                        <p className="text-sm text-muted-foreground">
                            Avg. Processing Time: <span className="font-medium text-foreground">{scorecard.avg_processing_days.toFixed(1)} days</span>
                        </p>
                    </div>
                </Card>
            )}

            {/* Spend Overview */}
            {spend && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card className="p-6">
                        <h3 className="font-semibold mb-4">Total Spend</h3>
                        <p className="text-3xl font-bold">{formatCurrency(spend.total_spend_cents, spend.currency)}</p>
                    </Card>

                    <Card className="p-6">
                        <h3 className="font-semibold mb-4">Spend by Month</h3>
                        {spend.by_month.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No spend data available</p>
                        ) : (
                            <div className="space-y-3">
                                {spend.by_month.slice(-6).map((item) => (
                                    <div key={item.month} className="flex items-center justify-between">
                                        <span className="text-sm text-muted-foreground">{item.month}</span>
                                        <span className="text-sm font-medium">{formatCurrency(item.amount_cents, spend.currency)}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Card>
                </div>
            )}

            {!scorecard && !spend && (
                <Card className="p-12 text-center">
                    <p className="text-muted-foreground">No analytics data available yet. Complete some orders to see your metrics.</p>
                </Card>
            )}
        </div>
    );
}
