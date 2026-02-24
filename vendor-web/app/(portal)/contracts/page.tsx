"use client";

import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { contractService } from "@/lib/api/contracts";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Contract } from "@/types/models";

const STATUS_FILTERS = ["ALL", "ACTIVE", "DRAFT", "EXPIRED", "TERMINATED"];

export default function ContractsPage() {
    const [data, setData] = useState<Contract[]>([]);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState("ALL");

    const fetchData = async (p: number, s: string) => {
        setLoading(true);
        try {
            const params: Record<string, any> = { page: p, per_page: 20 };
            if (s !== "ALL") params.status = s;
            const res = await contractService.list(params);
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
            <div>
                <h1 className="text-2xl font-bold">Contracts</h1>
                <p className="text-muted-foreground">View your active contracts and agreements</p>
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
                    { header: "Contract #", accessorKey: "contract_number", sortable: true },
                    { header: "Title", accessorKey: "title" },
                    {
                        header: "Status",
                        cell: (row) => <StatusBadge status={row.status} />,
                    },
                    {
                        header: "Value",
                        cell: (row) => formatCurrency(row.total_value_cents, row.currency),
                        sortable: true,
                        accessorKey: "total_value_cents",
                    },
                    {
                        header: "Start",
                        cell: (row) => formatDate(row.start_date),
                        sortable: true,
                        accessorKey: "start_date",
                    },
                    {
                        header: "End",
                        cell: (row) => formatDate(row.end_date),
                        sortable: true,
                        accessorKey: "end_date",
                    },
                ]}
                data={data}
                loading={loading}
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
                emptyMessage="No contracts found."
            />
        </div>
    );
}
