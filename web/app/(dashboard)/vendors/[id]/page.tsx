"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle, Ban } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { vendorService } from "@/lib/api/vendors";
import { formatDate } from "@/lib/utils";
import type { Vendor } from "@/types/models";
import { toast } from "sonner";

export default function VendorDetailPage() {
    const params = useParams();
    const router = useRouter();
    const [vendor, setVendor] = useState<Vendor | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        vendorService.get(params.id as string).then(setVendor).catch(() => toast.error("Failed to load vendor")).finally(() => setLoading(false));
    }, [params.id]);

    if (loading) return <div className="flex justify-center py-20"><div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" /></div>;
    if (!vendor) return <p>Vendor not found</p>;

    async function handleApprove() {
        try { await vendorService.approve(vendor!.id); toast.success("Vendor approved"); setVendor({ ...vendor!, status: "ACTIVE" }); } catch { toast.error("Failed"); }
    }
    async function handleBlock() {
        const reason = prompt("Block reason:");
        if (!reason) return;
        try { await vendorService.block(vendor!.id, reason); toast.success("Vendor blocked"); setVendor({ ...vendor!, status: "BLOCKED" }); } catch { toast.error("Failed"); }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()}><ArrowLeft className="h-4 w-4" /></Button>
                <div className="flex-1">
                    <h1 className="text-2xl font-bold">{vendor.legal_name}</h1>
                    <p className="text-muted-foreground">{vendor.email}</p>
                </div>
                <StatusBadge status={vendor.status} />
                {vendor.status === "PENDING_REVIEW" && (
                    <Button onClick={handleApprove} variant="success" size="sm"><CheckCircle className="mr-2 h-4 w-4" />Approve</Button>
                )}
                {vendor.status === "ACTIVE" && (
                    <Button onClick={handleBlock} variant="destructive" size="sm"><Ban className="mr-2 h-4 w-4" />Block</Button>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader><CardTitle className="text-lg">Details</CardTitle></CardHeader>
                    <CardContent className="space-y-3 text-sm">
                        <Row label="Tax ID" value={vendor.tax_id} />
                        <Row label="Phone" value={vendor.phone || "—"} />
                        <Row label="Risk Score" value={String(vendor.risk_score)} />
                        <Row label="Rating" value={`${vendor.rating}/10`} />
                        <Row label="Created" value={formatDate(vendor.created_at)} />
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

function Row({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex justify-between"><span className="text-muted-foreground">{label}</span><span className="font-medium">{value}</span></div>
    );
}
