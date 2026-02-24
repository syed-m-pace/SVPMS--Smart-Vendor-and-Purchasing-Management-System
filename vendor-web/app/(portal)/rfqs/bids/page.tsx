"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, History } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { rfqService } from "@/lib/api/rfqs";
import { useAuthStore } from "@/lib/stores/auth";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { RFQ } from "@/types/models";

interface BidHistoryEntry {
    rfq_id: string;
    rfq_number: string;
    rfq_title: string;
    rfq_status: string;
    bid_amount_cents: number;
    delivery_days: number | null | undefined;
    submitted_at: string;
    won: boolean;
}

export default function BidHistoryPage() {
    const router = useRouter();
    const vendor = useAuthStore((s) => s.vendor);
    const [entries, setEntries] = useState<BidHistoryEntry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchAll = async () => {
            try {
                // Fetch all RFQs the vendor has interacted with
                const res = await rfqService.list({ per_page: 100 });
                const history: BidHistoryEntry[] = [];
                for (const rfq of res.data) {
                    const myBid = rfq.bids?.find((b) => vendor && b.vendor_id === vendor.id);
                    if (myBid) {
                        history.push({
                            rfq_id: rfq.id,
                            rfq_number: rfq.rfq_number,
                            rfq_title: rfq.title,
                            rfq_status: rfq.status,
                            bid_amount_cents: myBid.total_cents,
                            delivery_days: myBid.delivery_days,
                            submitted_at: myBid.submitted_at,
                            won: rfq.status === "AWARDED" && rfq.awarded_vendor_id === vendor?.id,
                        });
                    }
                }
                setEntries(history);
            } catch {
                setEntries([]);
            } finally {
                setLoading(false);
            }
        };
        fetchAll();
    }, [vendor]);

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.push("/rfqs")}>
                    <ArrowLeft className="h-5 w-5" />
                </Button>
                <div>
                    <h1 className="text-2xl font-bold">Bid History</h1>
                    <p className="text-muted-foreground">All bids you&apos;ve submitted across RFQs</p>
                </div>
            </div>

            <DataTable
                columns={[
                    { header: "RFQ Number", accessorKey: "rfq_number" as any, sortable: true },
                    { header: "Title", accessorKey: "rfq_title" as any },
                    {
                        header: "RFQ Status",
                        cell: (row) => <StatusBadge status={row.rfq_status} />,
                    },
                    {
                        header: "Bid Amount",
                        cell: (row) => formatCurrency(row.bid_amount_cents),
                        sortable: true,
                        accessorKey: "bid_amount_cents" as any,
                    },
                    {
                        header: "Lead Time",
                        cell: (row) => row.delivery_days ? `${row.delivery_days} days` : "—",
                    },
                    {
                        header: "Submitted",
                        cell: (row) => formatDate(row.submitted_at),
                        sortable: true,
                        accessorKey: "submitted_at" as any,
                    },
                    {
                        header: "Result",
                        cell: (row) => {
                            if (row.won) return <span className="text-sm font-semibold text-success">Won</span>;
                            if (row.rfq_status === "AWARDED") return <span className="text-sm text-destructive">Lost</span>;
                            if (row.rfq_status === "OPEN") return <span className="text-sm text-muted-foreground">Pending</span>;
                            return "—";
                        },
                    },
                ]}
                data={entries}
                loading={loading}
                onRowClick={(row) => router.push(`/rfqs/${row.rfq_id}`)}
                emptyMessage="No bids submitted yet."
            />
        </div>
    );
}
