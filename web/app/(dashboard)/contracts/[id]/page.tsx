"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle, XCircle, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { contractService } from "@/lib/api/contracts";
import { vendorService } from "@/lib/api/vendors";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Contract, Vendor } from "@/types/models";
import { toast } from "sonner";
import { isAxiosError } from "axios";
import { useAuthStore } from "@/lib/stores/auth";

export default function ContractDetailPage() {
    const params = useParams();
    const router = useRouter();
    const { user } = useAuthStore();
    const [contract, setContract] = useState<Contract | null>(null);
    const [loading, setLoading] = useState(true);
    const [activating, setActivating] = useState(false);
    const [terminating, setTerminating] = useState(false);
    const [terminateDialogOpen, setTerminateDialogOpen] = useState(false);
    const [terminateReason, setTerminateReason] = useState("");

    // Vendor Assignment State
    const [assignDialogOpen, setAssignDialogOpen] = useState(false);
    const [allVendors, setAllVendors] = useState<Vendor[]>([]);
    const [selectedVendors, setSelectedVendors] = useState<string[]>([]);
    const [assigning, setAssigning] = useState(false);

    const canManageContracts = ["admin", "procurement_lead", "manager", "finance_head", "cfo"].includes(user?.role || "");

    const getErrorMessage = (error: unknown, fallback: string) => {
        if (isAxiosError(error)) {
            const detail = error.response?.data?.detail;
            if (typeof detail === "string") return detail;
        }
        return fallback;
    };

    useEffect(() => {
        contractService.get(params.id as string).then(setContract).catch(() => toast.error("Failed to load contract")).finally(() => setLoading(false));
    }, [params.id]);

    const handleActivate = async () => {
        if (!contract) return;
        setActivating(true);
        try {
            const updated = await contractService.activate(contract.id);
            setContract(updated);
            toast.success("Contract successfully activated");
        } catch (error) {
            toast.error(getErrorMessage(error, "Failed to activate contract"));
        } finally {
            setActivating(false);
        }
    };

    const handleTerminate = async () => {
        if (!contract || terminateReason.trim().length < 5) return;
        setTerminating(true);
        try {
            const updated = await contractService.terminate(contract.id, terminateReason);
            setContract(updated);
            toast.success("Contract terminated");
            setTerminateDialogOpen(false);
        } catch (error) {
            toast.error(getErrorMessage(error, "Failed to terminate contract"));
        } finally {
            setTerminating(false);
        }
    };

    const handleOpenAssignDialog = async () => {
        try {
            const resp = await vendorService.list({ limit: 100, status: "ACTIVE" });
            setAllVendors(resp.data);

            // Pre-select already assigned vendors
            const preSelected = contract?.assigned_vendors?.map(v => v.vendor_id) || [];
            if (contract?.vendor_id && !preSelected.includes(contract.vendor_id)) {
                preSelected.push(contract.vendor_id);
            }
            setSelectedVendors(preSelected);
            setAssignDialogOpen(true);
        } catch (error) {
            toast.error("Failed to fetch vendors");
        }
    };

    const handleToggleVendor = (vid: string) => {
        setSelectedVendors(prev =>
            prev.includes(vid) ? prev.filter(id => id !== vid) : [...prev, vid]
        );
    };

    const handleAssignVendors = async () => {
        if (!contract) return;
        setAssigning(true);
        try {
            await contractService.assignVendors(contract.id, selectedVendors);
            const refresh = await contractService.get(contract.id);
            setContract(refresh);
            toast.success("Vendors successfully assigned");
            setAssignDialogOpen(false);
        } catch (error) {
            toast.error(getErrorMessage(error, "Failed to assign vendors"));
        } finally {
            setAssigning(false);
        }
    };

    if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>;
    if (!contract) return <p>Contract not found</p>;

    return (
        <div className="space-y-6 max-w-5xl mx-auto">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()}><ArrowLeft className="h-5 w-5" /></Button>
                <div className="flex-1">
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-bold font-mono">{contract.contract_number}</h1>
                        <StatusBadge status={contract.status} />
                    </div>
                    <p className="text-muted-foreground">{contract.title}</p>
                </div>
                {canManageContracts && contract.status === "DRAFT" && (
                    <Button onClick={handleActivate} disabled={activating} className="gap-2">
                        {activating ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                        Activate Contract
                    </Button>
                )}
                {canManageContracts && contract.status === "ACTIVE" && (
                    <Button
                        variant="outline"
                        onClick={() => setTerminateDialogOpen(true)}
                        disabled={terminating}
                        className="gap-2 border-destructive/50 text-destructive hover:bg-destructive/10"
                    >
                        <XCircle className="h-4 w-4" />
                        Terminate
                    </Button>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader><CardTitle className="text-lg flex items-center gap-2"><FileText className="h-5 w-5 text-muted-foreground" /> Primary Details</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <InfoRow label="Contract Number" value={contract.contract_number} />
                        {contract.vendor_id && (
                            <InfoRow label="Creator Vendor" value={contract.vendor_name || contract.vendor_id} />
                        )}
                        <InfoRow label="Total Value" value={contract.value_cents ? formatCurrency(contract.value_cents) : "—"} />
                        <InfoRow label="Start Date" value={formatDate(contract.start_date)} />
                        <InfoRow label="End Date" value={formatDate(contract.end_date)} />
                        <InfoRow label="Renewal Notice" value={`${contract.renewal_notice_days} days (${contract.auto_renew ? 'Auto-renews' : 'Manual'})`} />
                    </CardContent>
                </Card>

                <div className="space-y-6">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle className="text-lg">Assigned Vendors</CardTitle>
                            {canManageContracts && contract.status === "ACTIVE" && (
                                <Button variant="outline" size="sm" onClick={handleOpenAssignDialog}>
                                    Assign / Edit
                                </Button>
                            )}
                        </CardHeader>
                        <CardContent className="space-y-4 text-sm">
                            {contract.assigned_vendors && contract.assigned_vendors.length > 0 ? (
                                <div className="space-y-2">
                                    {contract.assigned_vendors.map((av) => (
                                        <div key={av.vendor_id} className="flex items-center justify-between p-2 border rounded-md">
                                            <span className="font-medium">{av.vendor_name}</span>
                                            <span className="text-xs text-muted-foreground font-mono">{av.vendor_id}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-muted-foreground italic text-center py-4">No specific vendors assigned. This acts as a Master Template.</p>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader><CardTitle className="text-lg">Terms & SLA</CardTitle></CardHeader>
                        <CardContent className="space-y-4 text-sm">
                            <div>
                                <p className="text-muted-foreground mb-1">Description</p>
                                <p className="bg-muted/30 p-3 rounded-md border min-h-[60px]">{contract.description || "No description provided."}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground mb-1">SLA Terms</p>
                                <p className="bg-muted/30 p-3 rounded-md border min-h-[60px]">{contract.sla_terms || "No distinct SLA terms detailed."}</p>
                            </div>
                            {contract.terminated_at && (
                                <div className="bg-destructive/10 text-destructive p-3 rounded-md mt-4 text-sm font-medium border border-destructive/20">
                                    Terminated on {formatDate(contract.terminated_at)}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>

            <AlertDialog open={terminateDialogOpen} onOpenChange={setTerminateDialogOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Terminate Contract &quot;{contract.contract_number}&quot;?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you absolutely sure you want to forcibly terminate this active contract?
                        </AlertDialogDescription>
                    </AlertDialogHeader>

                    <div className="py-2">
                        <Label htmlFor="terminate_reason" className="text-sm font-medium">Termination Reason (required)</Label>
                        <Input
                            id="terminate_reason"
                            className="mt-1"
                            placeholder="e.g. Breach of SLA"
                            value={terminateReason}
                            onChange={(e) => setTerminateReason(e.target.value)}
                        />
                    </div>

                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={terminating}>Keep Contract</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(e) => { e.preventDefault(); handleTerminate(); }}
                            disabled={terminating || terminateReason.trim().length < 5}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {terminating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Terminate
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>Assign Vendors to Contract</DialogTitle>
                        <DialogDescription>
                            Select the vendor(s) this Master Contract applies to. They will be notified automatically.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="py-4 space-y-4 max-h-[350px] overflow-y-auto pr-2">
                        {allVendors.length === 0 ? (
                            <p className="text-center text-muted-foreground text-sm">No active vendors found.</p>
                        ) : (
                            allVendors.map(vendor => (
                                <div key={vendor.id} className="flex items-center space-x-3 p-2 rounded hover:bg-muted/50 transition-colors">
                                    <Checkbox
                                        id={vendor.id}
                                        checked={selectedVendors.includes(vendor.id)}
                                        onCheckedChange={() => handleToggleVendor(vendor.id)}
                                    />
                                    <Label htmlFor={vendor.id} className="flex flex-col flex-1 cursor-pointer">
                                        <span className="font-medium text-sm">{vendor.legal_name}</span>
                                        <span className="text-xs text-muted-foreground">{vendor.email}</span>
                                    </Label>
                                </div>
                            ))
                        )}
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setAssignDialogOpen(false)} disabled={assigning}>Cancel</Button>
                        <Button onClick={handleAssignVendors} disabled={assigning || selectedVendors.length === 0}>
                            {assigning && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Assign Selected ({selectedVendors.length})
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
    return (
        <div className="flex items-center justify-between pb-2 border-b border-muted/50 last:border-0 last:pb-0">
            <span className="text-sm text-muted-foreground">{label}</span>
            <span className="text-sm font-medium text-right max-w-[60%] truncate">{value}</span>
        </div>
    );
}
