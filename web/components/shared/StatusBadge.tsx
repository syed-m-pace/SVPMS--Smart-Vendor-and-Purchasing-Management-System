import { Badge } from "@/components/ui/badge";

const statusConfig: Record<string, { label: string; variant: "success" | "warning" | "destructive" | "accent" | "info" | "secondary" | "outline" }> = {
    // PR statuses
    DRAFT: { label: "Draft", variant: "warning" },
    PENDING: { label: "Pending", variant: "accent" },
    APPROVED: { label: "Approved", variant: "success" },
    REJECTED: { label: "Rejected", variant: "destructive" },
    CANCELLED: { label: "Cancelled", variant: "secondary" },

    // PO statuses
    ISSUED: { label: "Issued", variant: "accent" },
    ACKNOWLEDGED: { label: "Acknowledged", variant: "info" },
    PARTIALLY_RECEIVED: { label: "Partial", variant: "warning" },
    FULLY_RECEIVED: { label: "Received", variant: "success" },
    PARTIALLY_FULFILLED: { label: "Partial", variant: "warning" },
    FULFILLED: { label: "Fulfilled", variant: "success" },
    CLOSED: { label: "Closed", variant: "secondary" },

    // Invoice statuses
    UPLOADED: { label: "Uploaded", variant: "accent" },
    SUBMITTED: { label: "Submitted", variant: "accent" },
    UNDER_REVIEW: { label: "Reviewing", variant: "info" },
    MATCHED: { label: "Matched", variant: "success" },
    DISPUTED: { label: "Disputed", variant: "warning" },
    PAID: { label: "Paid", variant: "success" },
    EXCEPTION: { label: "Exception", variant: "destructive" },

    // Match statuses
    MISMATCHED: { label: "Mismatched", variant: "destructive" },
    PASS: { label: "Pass", variant: "success" },
    FAIL: { label: "Fail", variant: "destructive" },
    OVERRIDE: { label: "Override", variant: "warning" },

    // Vendor statuses
    ACTIVE: { label: "Active", variant: "success" },
    PENDING_REVIEW: { label: "Pending Review", variant: "warning" },
    BLOCKED: { label: "Blocked", variant: "destructive" },
    ARCHIVED: { label: "Archived", variant: "secondary" },
};

interface StatusBadgeProps {
    status: string;
    className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
    const config = statusConfig[status] || {
        label: status,
        variant: "outline" as const,
    };
    return (
        <Badge variant={config.variant} className={className}>
            {config.label}
        </Badge>
    );
}
