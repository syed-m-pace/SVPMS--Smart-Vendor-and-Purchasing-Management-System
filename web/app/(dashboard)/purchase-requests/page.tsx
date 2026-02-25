"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { prService } from "@/lib/api/purchase-requests";
import { formatCurrency, timeAgo } from "@/lib/utils";
import type { PurchaseRequest } from "@/types/models";

export default function PurchaseRequestsPage() {
    const router = useRouter();
    const [prs, setPrs] = useState<PurchaseRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [statusFilter, setStatusFilter] = useState("");
    const [search, setSearch] = useState("");

    useEffect(() => { load(); }, [page, statusFilter]);

    async function load() {
        setLoading(true);
        try {
            const res = await prService.list({ page, status: statusFilter || undefined });
            setPrs(res.data);
            setTotalPages(res.pagination.total_pages);
        } catch { /* ignore */ } finally { setLoading(false); }
    }

    const filteredPrs = search
        ? prs.filter((pr) =>
            pr.pr_number?.toLowerCase().includes(search.toLowerCase()) ||
            pr.description?.toLowerCase().includes(search.toLowerCase())
        )
        : prs;

    const columns = [
        { header: "PR Number", cell: (pr: PurchaseRequest) => <span className="font-mono font-medium">{pr.pr_number}</span> },
        { header: "Description", cell: (pr: PurchaseRequest) => <span className="truncate max-w-[200px] block">{pr.description || "---"}</span> },
        { header: "Status", cell: (pr: PurchaseRequest) => <StatusBadge status={pr.status} /> },
        { header: "Amount", cell: (pr: PurchaseRequest) => <span className="font-mono">{formatCurrency(pr.total_cents)}</span> },
        { header: "Created", cell: (pr: PurchaseRequest) => <span className="text-muted-foreground">{timeAgo(pr.created_at)}</span> },
    ];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Purchase Requests</h1>
                    <p className="text-muted-foreground mt-1">Create and track purchase requests</p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input placeholder="Search PRs..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9 w-[200px]" />
                    </div>
                    <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 appearance-none pr-8" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 8px center' }}>
                        <option value="">All Statuses</option>
                        {["DRAFT", "PENDING", "APPROVED", "REJECTED", "CANCELLED"].map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <Button asChild><Link href="/purchase-requests/new"><Plus className="mr-2 h-4 w-4" />New PR</Link></Button>
                </div>
            </div>
            <DataTable columns={columns} data={filteredPrs} loading={loading} page={page} totalPages={totalPages} onPageChange={setPage} onRowClick={(pr) => router.push(`/purchase-requests/${pr.id}`)} />
        </div>
    );
}
