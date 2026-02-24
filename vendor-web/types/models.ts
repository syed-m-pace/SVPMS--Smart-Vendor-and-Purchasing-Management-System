/* ── Domain Models (Vendor Portal) ── */

export interface User {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    role: string;
    department_id: string | null;
    is_active: boolean;
    tenant_id: string;
    profile_photo_url?: string | null;
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

export type VendorStatus = "DRAFT" | "PENDING_REVIEW" | "ACTIVE" | "BLOCKED" | "ARCHIVED";

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
}

export type POStatus =
    | "DRAFT"
    | "ISSUED"
    | "ACKNOWLEDGED"
    | "PARTIALLY_RECEIVED"
    | "FULLY_RECEIVED"
    | "FULFILLED"
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
    po_number?: string | null;
    status: InvoiceStatus;
    total_cents: number;
    currency: string;
    invoice_date?: string | null;
    due_date?: string | null;
    match_status: MatchStatus | null;
    ocr_status: string | null;
    document_url: string | null;
    ocr_data: Record<string, unknown> | null;
    match_exceptions: Record<string, unknown> | null;
    approved_payment_at?: string | null;
    paid_at?: string | null;
    line_items: InvoiceLineItem[];
    created_at: string;
    updated_at: string;
}

export type InvoiceStatus =
    | "UPLOADED"
    | "MATCHED"
    | "DISPUTED"
    | "EXCEPTION"
    | "APPROVED"
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

export interface RFQ {
    id: string;
    tenant_id: string;
    rfq_number: string;
    title: string;
    description?: string | null;
    pr_id: string | null;
    status: RFQStatus;
    deadline: string | null;
    budget_cents?: number | null;
    awarded_vendor_id?: string | null;
    awarded_po_id?: string | null;
    created_at: string;
    line_items?: RFQLineItem[];
    bids?: RFQBid[];
}

export type RFQStatus = "DRAFT" | "OPEN" | "CLOSED" | "AWARDED" | "CANCELLED";

export interface RFQLineItem {
    id: string;
    description: string;
    quantity: number;
    unit?: string | null;
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

export interface Contract {
    id: string;
    tenant_id: string;
    contract_number: string;
    vendor_id: string;
    title: string;
    status: "DRAFT" | "ACTIVE" | "EXPIRED" | "TERMINATED";
    start_date: string;
    end_date: string;
    total_value_cents: number;
    currency: string;
    created_at: string;
}

export interface VendorScorecard {
    vendor_id: string;
    on_time_delivery_pct: number;
    invoice_acceptance_pct: number;
    fulfillment_rate_pct: number;
    rfq_response_pct: number;
    avg_processing_days: number;
    overall_score: number;
}

export interface DashboardStats {
    pending_prs: number;
    active_pos: number;
    invoice_exceptions: number;
    open_invoices: number;
    pending_rfqs: number;
    budget_utilization: number;
}

export interface AppNotification {
    id: string;
    type: "po" | "rfq" | "invoice" | "payment" | "general";
    title: string;
    body: string;
    entity_id?: string;
    read: boolean;
    created_at: string;
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
