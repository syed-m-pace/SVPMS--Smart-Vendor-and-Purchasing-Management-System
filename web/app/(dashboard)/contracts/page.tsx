"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { contractService } from "@/lib/api/contracts";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Contract } from "@/types/models";
import { useRouter } from "next/navigation";

const STATUS_FILTERS = ["ALL", "ACTIVE", "DRAFT", "EXPIRED", "TERMINATED"];

export default function AdminContractsPage() {
    const router = useRouter();
    const [data, setData] = useState<Contract[]>([]);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState("ALL");

    const fetchData = async (p: number, s: string) => {
        setLoading(true);
        try {
            const params: Record<string, string | number> = { page: p, per_page: 20 };
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
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Contracts</h1>
                    <p className="text-muted-foreground">Manage vendor contracts and compliance</p>
                </div>
                <Button onClick={() => router.push("/contracts/new")}>
                    <Plus className="h-4 w-4 mr-2" /> New Contract
                </Button>
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
                    { header: "Contract #", accessorKey: "contract_number" },
                    { header: "Vendor", cell: (row) => row.vendor_name || row.vendor_id.substring(0, 8) },
                    { header: "Title", accessorKey: "title" },
                    {
                        header: "Status",
                        cell: (row) => <StatusBadge status={row.status} />,
                    },
                    {
                        header: "Value",
                        cell: (row) => row.value_cents ? formatCurrency(row.value_cents) : "—",
                    },
                    {
                        header: "Start",
                        cell: (row) => formatDate(row.start_date),
                    },
                    {
                        header: "End",
                        cell: (row) => formatDate(row.end_date),
                    },
                ]}
                data={data}
                loading={loading}
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
                onRowClick={(row) => router.push(`/contracts/${row.id}`)}
                emptyMessage="No contracts found."
            />
        </div>
    );
}
