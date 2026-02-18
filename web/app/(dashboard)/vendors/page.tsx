"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { vendorService } from "@/lib/api/vendors";
import type { Vendor } from "@/types/models";

export default function VendorsPage() {
    const router = useRouter();
    const [vendors, setVendors] = useState<Vendor[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    useEffect(() => {
        load();
    }, [page, search]);

    async function load() {
        setLoading(true);
        try {
            const res = await vendorService.list({ page, search: search || undefined });
            setVendors(res.data);
            setTotalPages(res.pagination.total_pages);
        } catch { /* ignore */ } finally {
            setLoading(false);
        }
    }

    const columns = [
        {
            header: "Vendor Name",
            cell: (v: Vendor) => (
                <span className="font-medium">{v.legal_name}</span>
            ),
        },
        { header: "Tax ID", accessorKey: "tax_id" as keyof Vendor },
        { header: "Email", accessorKey: "email" as keyof Vendor },
        {
            header: "Status",
            cell: (v: Vendor) => <StatusBadge status={v.status} />,
        },
        {
            header: "Risk Score",
            cell: (v: Vendor) => (
                <span className={v.risk_score && v.risk_score > 50 ? "text-destructive font-bold" : ""}>
                    {v.risk_score ?? "-"}
                </span>
            ),
        },
    ];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Vendors</h1>
                    <p className="text-muted-foreground mt-1">Manage vendor registry</p>
                </div>
                <Button asChild>
                    <Link href="/vendors/new"><Plus className="mr-2 h-4 w-4" />Add Vendor</Link>
                </Button>
            </div>

            <div className="flex gap-4">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search vendors..."
                        value={search}
                        onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                        className="pl-10"
                    />
                </div>
            </div>

            <DataTable
                columns={columns}
                data={vendors}
                loading={loading}
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
                onRowClick={(v) => router.push(`/vendors/${v.id}`)}
            />
        </div>
    );
}
