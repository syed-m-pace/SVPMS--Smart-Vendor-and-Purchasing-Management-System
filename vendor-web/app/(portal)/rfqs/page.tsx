"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Gavel, History } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { rfqService } from "@/lib/api/rfqs";
import { useAuthStore } from "@/lib/stores/auth";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { RFQ } from "@/types/models";

const STATUS_FILTERS = ["ALL", "OPEN", "AWARDED", "CLOSED"];

export default function RFQsPage() {
    const router = useRouter();
    const vendor = useAuthStore((s) => s.vendor);
    const [data, setData] = useState<RFQ[]>([]);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState("ALL");

    const fetchData = async (p: number, s: string) => {
        setLoading(true);
        try {
            const params: Record<string, any> = { page: p, per_page: 20 };
            if (s !== "ALL") params.status = s;
            const res = await rfqService.list(params);
            setData(res.data);
            setTotalPages(res.pagination.total_pages);
        } catch {
            setData([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData(page, status);
    }, [page, status]);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Requests for Quotation</h1>
                    <p className="text-muted-foreground">View open RFQs and submit your bids</p>
                </div>
                <Link href="/rfqs/bids">
                    <Button variant="outline">
                        <History className="h-4 w-4 mr-2" /> Bid History
                    </Button>
                </Link>
            </div>

            <div className="flex flex-wrap gap-2">
                {STATUS_FILTERS.map((s) => (
                    <Button
                        key={s}
                        variant={status === s ? "default" : "outline"}
                        size="sm"
                        onClick={() => { setStatus(s); setPage(1); }}
                    >
                        {s === "ALL" ? "All" : s}
                    </Button>
                ))}
            </div>

            <DataTable
                columns={[
                    { header: "RFQ Number", accessorKey: "rfq_number", sortable: true },
                    { header: "Title", accessorKey: "title" },
                    {
                        header: "Status",
                        cell: (row) => <StatusBadge status={row.status} />,
                    },
                    {
                        header: "Budget",
                        cell: (row) => row.budget_cents ? formatCurrency(row.budget_cents) : "—",
                        sortable: true,
                        accessorKey: "budget_cents",
                    },
                    {
                        header: "Deadline",
                        cell: (row) => formatDate(row.deadline),
                        sortable: true,
                        accessorKey: "deadline",
                    },
                    {
                        header: "Bid",
                        cell: (row) => {
                            const myBid = row.bids?.find((b) => b.vendor_id);
                            if (row.status === "AWARDED") {
                                if (row.awarded_vendor_id === vendor?.id) {
                                    return <span className="text-sm font-medium text-success">Won</span>;
                                }
                                if (myBid) {
                                    return <span className="text-sm font-medium text-destructive">Lost</span>;
                                }
                                return <span className="text-sm text-muted-foreground">Awarded</span>;
                            }
                            if (myBid) {
                                return <span className="text-sm text-accent">Bid Submitted</span>;
                            }
                            if (row.status === "OPEN") {
                                return <span className="text-sm text-muted-foreground">No bid</span>;
                            }
                            return "—";
                        },
                    },
                ]}
                data={data}
                loading={loading}
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
                onRowClick={(row) => router.push(`/rfqs/${row.id}`)}
                emptyMessage="No RFQs found."
            />
        </div>
    );
}
