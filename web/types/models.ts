/* ── Domain Models ── */

export interface User {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    role: UserRole;
    department_id: string;
    is_active: boolean;
    tenant_id: string;
    created_at: string;
}

export type UserRole =
    | "admin"
    | "manager"
    | "procurement_lead"
    | "procurement"
    | "finance"
    | "finance_head"
    | "cfo"
    | "viewer"
    | "vendor";

export interface Department {
    id: string;
    tenant_id: string;
    name: string;
    code: string;
    manager_id: string | null;
    parent_department_id: string | null;
    created_at: string;
}

export interface Vendor {
    id: string;
    tenant_id: string;
    legal_name: string;
    trade_name: string | null;
    tax_id: string;
    email: string;
    phone: string;
    status: VendorStatus;
    risk_score: number;
    rating: number;
    bank_name?: string | null;
    ifsc_code?: string | null;
    bank_account?: string | null;
    contact_person?: string | null;
    created_at: string;
}

export type VendorStatus =
    | "DRAFT"
    | "PENDING_REVIEW"
    | "ACTIVE"
    | "BLOCKED"
    | "ARCHIVED";

export interface Budget {
    id: string;
    tenant_id: string;
    department_id: string;
    fiscal_year: number;
    quarter: number;
    total_cents: number;
    spent_cents: number;
    reserved_cents: number;
    currency: string;
    department?: Department;
}

export interface PurchaseRequest {
    id: string;
    tenant_id: string;
    pr_number: string;
    requester_id: string;
    department_id: string;
    status: PRStatus;
    total_cents: number;
    currency: string;
    description: string | null;
    justification: string | null;
    line_items: PRLineItem[];
    created_at: string;
    updated_at: string;
    submitted_at: string | null;
    approved_at: string | null;
    requester?: User;
    department?: Department;
}

export type PRStatus =
    | "DRAFT"
    | "PENDING"
    | "APPROVED"
    | "REJECTED"
    | "CANCELLED";

export interface PRLineItem {
    id: string;
    pr_id: string;
    line_number: number;
    description: string;
    quantity: number;
    unit_price_cents: number;
    category: string | null;
    notes: string | null;
}

export interface PurchaseOrder {
    id: string;
    tenant_id: string;
    po_number: string;
    pr_id: string | null;
    vendor_id: string;
    vendor_name?: string | null;
    status: POStatus;
    total_cents: number;
    currency: string;
    issued_at: string | null;
    expected_delivery_date?: string | null;
    terms_and_conditions?: string | null;
    line_items: POLineItem[];
    created_at: string;
    updated_at: string;
    vendor?: Vendor;
}

export interface PurchaseOrderReady {
    pr_id: string;
    pr_number: string;
    requester_id: string;
    department_id: string;
    total_cents: number;
    currency: string;
    description: string | null;
    approved_at: string | null;
    created_at: string;
}

export type POStatus =
    | "DRAFT"
    | "ISSUED"
    | "ACKNOWLEDGED"
    | "PARTIALLY_RECEIVED"
    | "FULLY_RECEIVED"
    | "CANCELLED"
    | "CLOSED";

export interface POLineItem {
    id: string;
    po_id: string;
    line_number: number;
    description: string;
    quantity: number;
    unit_price_cents: number;
    received_quantity: number;
}

export interface Invoice {
    id: string;
    tenant_id: string;
    invoice_number: string;
    vendor_id: string;
    vendor_name?: string | null;
    po_id: string | null;
    status: InvoiceStatus;
    total_cents: number;
    currency: string;
    match_status: MatchStatus | null;
    ocr_status: string | null;
    document_url: string | null;
    ocr_data: Record<string, unknown> | null;
    match_exceptions: Record<string, unknown> | null;
    line_items: InvoiceLineItem[];
    created_at: string;
    updated_at: string;
    vendor?: Vendor;
}

export type InvoiceStatus =
    | "UPLOADED"
    | "MATCHED"
    | "DISPUTED"
    | "EXCEPTION"
    | "PAID"
    | "REJECTED";

export type MatchStatus = "PASS" | "FAIL" | "OVERRIDE" | "MATCHED" | "MISMATCHED" | "PENDING";

export interface InvoiceLineItem {
    id: string;
    invoice_id: string;
    line_number: number;
    description: string;
    quantity: number;
    unit_price_cents: number;
}

export interface Receipt {
    id: string;
    tenant_id: string;
    receipt_number: string;
    po_id: string;
    received_by_id: string;
    received_at: string;
    notes: string | null;
    line_items: ReceiptLineItem[];
    created_at: string;
}

export interface ReceiptLineItem {
    id: string;
    receipt_id: string;
    po_line_item_id: string;
    quantity_received: number;
    notes: string | null;
}

export interface Approval {
    id: string;
    tenant_id: string;
    entity_type: string;
    entity_id: string;
    approver_id: string;
    approval_level: number;
    status: ApprovalStatus;
    comments: string | null;
    approved_at: string | null;
    created_at: string;
    // enriched fields from API
    entity_number?: string;
    requester_name?: string;
    department_name?: string;
    total_cents?: number;
    description?: string;
}

export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED";

export interface RFQLineItem {
    id: string;
    description: string;
    quantity: number;
    specifications?: string | null;
}

export interface RFQBid {
    id: string;
    rfq_id: string;
    vendor_id: string;
    total_cents: number;
    delivery_days?: number | null;
    notes?: string | null;
    score?: number | null;
    submitted_at: string;
}

export interface RFQ {
    id: string;
    tenant_id: string;
    rfq_number: string;
    title: string;
    pr_id: string | null;
    status: string;
    deadline: string | null;
    awarded_vendor_id?: string | null;
    awarded_po_id?: string | null;
    created_at: string;
    line_items?: RFQLineItem[];
    bids?: RFQBid[];
}

/* ── API Response Wrappers ── */
export interface PaginatedResponse<T> {
    data: T[];
    pagination: {
        page: number;
        per_page: number;
        total: number;
        total_pages: number;
    };
}

export interface AuthResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface DashboardStats {
    pending_prs: number;
    active_pos: number;
    invoice_exceptions: number;
    budget_utilization: number;
}
