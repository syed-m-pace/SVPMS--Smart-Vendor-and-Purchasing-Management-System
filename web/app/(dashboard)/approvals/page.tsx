"use client";

import { useEffect, useState } from "react";
import { CheckCircle, XCircle, Loader2, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { approvalService } from "@/lib/api/services";
import { formatCurrency, timeAgo } from "@/lib/utils";
import type { Approval } from "@/types/models";
import { toast } from "sonner";
import { useUIStore } from "@/lib/stores/ui";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

export default function ApprovalsPage() {
    const [approvals, setApprovals] = useState<Approval[]>([]);
    const [loading, setLoading] = useState(true);
    const [actionId, setActionId] = useState<string | null>(null);
    const [rejectId, setRejectId] = useState<string | null>(null);
    const [rejectReason, setRejectReason] = useState("");
    const triggerRefresh = useUIStore((s) => s.triggerRefreshNotifications);

    useEffect(() => { load(); }, []);

    async function load() {
        setLoading(true);
        try {
            const res = await approvalService.listPending();
            setApprovals(res.data);
        } catch { } finally { setLoading(false); }
    }

    async function handleApprove(id: string) {
        setActionId(id);
        try {
            await approvalService.approve(id, "Approved via web");
            toast.success("Approved");
            setApprovals(prev => prev.filter(a => a.id !== id));
            triggerRefresh();
        } catch (e: any) { toast.error(e.response?.data?.detail?.error?.message || "Failed"); } finally { setActionId(null); }
    }

    async function confirmReject() {
        if (!rejectId || !rejectReason.trim()) return;
        setActionId(rejectId);
        try {
            await approvalService.reject(rejectId, rejectReason);
            toast.success("Rejected");
            setApprovals(prev => prev.filter(a => a.id !== rejectId));
            triggerRefresh();
            setRejectId(null);
            setRejectReason("");
        } catch (e: any) { toast.error(e.response?.data?.detail?.error?.message || "Failed"); } finally { setActionId(null); }
    }

    if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-accent" /></div>;

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Pending Approvals</h1>
                <p className="text-muted-foreground mt-1">{approvals.length} item{approvals.length !== 1 && "s"} awaiting your review</p>
            </div>

            {approvals.length === 0 ? (
                <Card>
                    <CardContent className="py-12 text-center">
                        <CheckCircle className="mx-auto h-12 w-12 text-success mb-4 opacity-50" />
                        <h3 className="text-lg font-medium">All caught up!</h3>
                        <p className="text-muted-foreground mt-1">No pending approvals</p>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-3">
                    {approvals.map((a) => (
                        <Card key={a.id} className="hover:shadow-md transition-shadow">
                            <CardContent className="p-5 flex items-center justify-between gap-4">
                                <div className="flex items-center gap-4 flex-1">
                                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent">
                                        <FileText className="h-5 w-5" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="font-medium">
                                            {a.entity_type} — {a.entity_number || a.entity_id.slice(0, 8)}
                                        </p>
                                        <p className="text-sm text-muted-foreground truncate">
                                            {a.requester_name && `From: ${a.requester_name}`}
                                            {a.total_cents != null && ` • ${formatCurrency(a.total_cents)}`}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                        Level {a.approval_level}
                                        <StatusBadge status={a.status} />
                                        <span>{timeAgo(a.created_at)}</span>
                                    </div>
                                </div>
                                <div className="flex gap-2 shrink-0">
                                    <Button size="sm" variant="success" onClick={() => handleApprove(a.id)} disabled={!!actionId}>
                                        {actionId === a.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4 mr-1" />}
                                        Approve
                                    </Button>
                                    <Button size="sm" variant="destructive" onClick={() => { setRejectId(a.id); setRejectReason(""); }} disabled={!!actionId}>
                                        <XCircle className="h-4 w-4 mr-1" />Reject
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            <Dialog open={!!rejectId} onOpenChange={(open) => !open && setRejectId(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Reject Request</DialogTitle>
                        <DialogDescription>Please provide a reason for rejection.</DialogDescription>
                    </DialogHeader>
                    <Textarea
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="Reason for rejection..."
                        rows={3}
                    />
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setRejectId(null)} disabled={!!actionId}>Cancel</Button>
                        <Button variant="destructive" onClick={confirmReject} disabled={!rejectReason.trim() || !!actionId}>
                            {actionId === rejectId && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Reject Request
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
