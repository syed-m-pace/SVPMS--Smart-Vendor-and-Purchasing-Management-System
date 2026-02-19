"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle, Ban, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { vendorService } from "@/lib/api/vendors";
import { useAuthStore } from "@/lib/stores/auth";
import { formatDate } from "@/lib/utils";
import type { Vendor } from "@/types/models";
import { toast } from "sonner";

import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

export default function VendorDetailPage() {
    const params = useParams();
    const router = useRouter();
    const user = useAuthStore((s) => s.user);
    const [vendor, setVendor] = useState<Vendor | null>(null);
    const [loading, setLoading] = useState(true);
    const [blockOpen, setBlockOpen] = useState(false);
    const [blockReason, setBlockReason] = useState("");
    const [processing, setProcessing] = useState(false);

    useEffect(() => {
        vendorService.get(params.id as string).then(setVendor).catch(() => toast.error("Failed to load vendor")).finally(() => setLoading(false));
    }, [params.id]);

    if (loading) return <div className="flex justify-center py-20"><div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" /></div>;
    if (!vendor) return <p>Vendor not found</p>;
    const canApprove = ["admin", "manager", "procurement_lead"].includes(user?.role || "");
    const canBlock = ["admin", "manager", "procurement_lead"].includes(user?.role || "");

    async function handleApprove() {
        setProcessing(true);
        try {
            const updated = await vendorService.approve(vendor!.id);
            toast.success("Vendor approved");
            setVendor(updated);
        } catch {
            toast.error("Failed to approve vendor");
        } finally {
            setProcessing(false);
        }
    }

    async function handleBlock() {
        if (!blockReason.trim()) return;
        setProcessing(true);
        try {
            await vendorService.block(vendor!.id, blockReason);
            toast.success("Vendor blocked");
            setVendor({ ...vendor!, status: "BLOCKED" });
            setBlockOpen(false);
            setBlockReason("");
        } catch { toast.error("Failed"); } finally { setProcessing(false); }
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
                {canApprove && (vendor.status === "DRAFT" || vendor.status === "PENDING_REVIEW") && (
                    <Button onClick={handleApprove} variant="success" size="sm" disabled={processing}>
                        {processing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle className="mr-2 h-4 w-4" />}
                        Approve
                    </Button>
                )}
                {canBlock && vendor.status === "ACTIVE" && (
                    <Button onClick={() => setBlockOpen(true)} variant="destructive" size="sm" disabled={processing}><Ban className="mr-2 h-4 w-4" />Block</Button>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader><CardTitle className="text-lg">Details</CardTitle></CardHeader>
                    <CardContent className="space-y-3 text-sm">
                        <Row label="Tax ID" value={vendor.tax_id} />
                        <Row label="Phone" value={vendor.phone || "—"} />
                        <Row label="Risk Score" value={String(vendor.risk_score ?? 0)} />
                        <Row label="Rating" value={`${vendor.rating ?? 0}/10`} />
                        <Row label="Created" value={formatDate(vendor.created_at)} />
                    </CardContent>
                </Card>
            </div>

            <Dialog open={blockOpen} onOpenChange={setBlockOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Block Vendor</DialogTitle>
                        <DialogDescription>Are you sure? This will prevent any new POs for this vendor.</DialogDescription>
                    </DialogHeader>
                    <Textarea
                        value={blockReason}
                        onChange={(e) => setBlockReason(e.target.value)}
                        placeholder="Reason for blocking..."
                        rows={3}
                    />
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setBlockOpen(false)} disabled={processing}>Cancel</Button>
                        <Button variant="destructive" onClick={handleBlock} disabled={!blockReason.trim() || processing}>
                            {processing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Block Vendor
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

function Row({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex justify-between"><span className="text-muted-foreground">{label}</span><span className="font-medium">{value}</span></div>
    );
}
