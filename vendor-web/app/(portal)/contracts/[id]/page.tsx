"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Calendar, Clock, RefreshCw, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { contractService } from "@/lib/api/contracts";
import { formatCurrency, formatDate } from "@/lib/utils";
import { toast } from "sonner";
import type { Contract } from "@/types/models";

export default function ContractDetailPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();
    const [contract, setContract] = useState<Contract | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        contractService
            .get(id)
            .then(setContract)
            .catch(() => toast.error("Failed to load contract"))
            .finally(() => setLoading(false));
    }, [id]);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-accent" />
            </div>
        );
    }

    if (!contract) {
        return (
            <div className="text-center py-20">
                <p className="text-muted-foreground">Contract not found</p>
                <Button variant="outline" className="mt-4" onClick={() => router.push("/contracts")}>
                    <ArrowLeft className="h-4 w-4 mr-2" /> Back
                </Button>
            </div>
        );
    }

    const valueCents = contract.value_cents ?? contract.total_value_cents ?? 0;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => router.push("/contracts")}>
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold">{contract.title}</h1>
                        <p className="text-muted-foreground">{contract.contract_number}</p>
                    </div>
                </div>
                <StatusBadge status={contract.status} />
            </div>

            {/* Terminated Banner */}
            {contract.status === "TERMINATED" && contract.terminated_at && (
                <Card className="p-4 border-destructive bg-destructive/5">
                    <p className="text-sm text-destructive font-medium">
                        This contract was terminated on {formatDate(contract.terminated_at)}
                    </p>
                </Card>
            )}

            {/* Details Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="p-5">
                    <h3 className="font-semibold mb-4">Contract Details</h3>
                    <div className="space-y-3">
                        <InfoRow label="Contract Number" value={contract.contract_number} />
                        <InfoRow label="Status" value={<StatusBadge status={contract.status} />} />
                        <InfoRow label="Value" value={valueCents > 0 ? formatCurrency(valueCents, contract.currency) : "---"} />
                        <InfoRow label="Currency" value={contract.currency} />
                        {contract.vendor_name && (
                            <InfoRow label="Vendor" value={contract.vendor_name} />
                        )}
                        <InfoRow label="Created" value={formatDate(contract.created_at)} />
                    </div>
                </Card>

                <Card className="p-5">
                    <h3 className="font-semibold mb-4">Dates & Renewal</h3>
                    <div className="space-y-3">
                        <InfoRow
                            label="Start Date"
                            value={
                                <span className="flex items-center gap-1.5">
                                    <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                                    {formatDate(contract.start_date)}
                                </span>
                            }
                        />
                        <InfoRow
                            label="End Date"
                            value={
                                <span className="flex items-center gap-1.5">
                                    <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                                    {formatDate(contract.end_date)}
                                </span>
                            }
                        />
                        <InfoRow
                            label="Auto-Renew"
                            value={
                                <span className="flex items-center gap-1.5">
                                    <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />
                                    {contract.auto_renew ? "Yes" : "No"}
                                </span>
                            }
                        />
                        {contract.renewal_notice_days && (
                            <InfoRow
                                label="Renewal Notice"
                                value={
                                    <span className="flex items-center gap-1.5">
                                        <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                                        {contract.renewal_notice_days} days
                                    </span>
                                }
                            />
                        )}
                    </div>
                </Card>
            </div>

            {/* Description */}
            {contract.description && (
                <Card className="p-5">
                    <h3 className="font-semibold mb-3">Description</h3>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">{contract.description}</p>
                </Card>
            )}

            {/* SLA Terms */}
            {contract.sla_terms && (
                <Card className="p-5">
                    <h3 className="font-semibold mb-3 flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        SLA Terms
                    </h3>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">{contract.sla_terms}</p>
                </Card>
            )}
        </div>
    );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
    return (
        <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{label}</span>
            <span className="text-sm font-medium">{value}</span>
        </div>
    );
}
