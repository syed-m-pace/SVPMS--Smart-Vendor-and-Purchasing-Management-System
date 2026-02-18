"""initial_schema

Revision ID: b064a15c0f06
Revises:
Create Date: 2026-02-17 01:56:35.035893+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b064a15c0f06'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tenants (no FKs)
    op.create_table('tenants',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('slug', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_index('idx_tenants_slug', 'tenants', ['slug'], unique=False)
    op.create_index('idx_tenants_status', 'tenants', ['status'], unique=False)

    # 2. departments (without manager_id FK — added after users)
    op.create_table('departments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=True),
    sa.Column('manager_id', sa.UUID(), nullable=True),
    sa.Column('parent_department_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['parent_department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'code', name='uq_department_tenant_code')
    )

    # 3. users (FK to tenants + departments)
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=True),
    sa.Column('first_name', sa.String(length=100), nullable=True),
    sa.Column('last_name', sa.String(length=100), nullable=True),
    sa.Column('role', sa.String(length=50), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('mfa_enabled', sa.Boolean(), nullable=False),
    sa.Column('fcm_token', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('last_login_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=False)
    op.create_index('idx_users_role', 'users', ['role'], unique=False)
    op.create_index('idx_users_tenant', 'users', ['tenant_id'], unique=False)

    # 4. Deferred FK: departments.manager_id -> users.id
    op.create_foreign_key(
        'fk_departments_manager_id', 'departments', 'users',
        ['manager_id'], ['id']
    )

    # 5. approvals
    op.create_table('approvals',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.UUID(), nullable=False),
    sa.Column('approver_id', sa.UUID(), nullable=False),
    sa.Column('approval_level', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('approved_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('approval_level > 0', name='chk_approval_level_positive'),
    sa.ForeignKeyConstraint(['approver_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_approvals_approver', 'approvals', ['approver_id', 'status'], unique=False)
    op.create_index('idx_approvals_entity', 'approvals', ['entity_type', 'entity_id'], unique=False)

    # 6. audit_logs
    op.create_table('audit_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('actor_id', sa.UUID(), nullable=True),
    sa.Column('actor_email', sa.String(length=255), nullable=True),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.UUID(), nullable=False),
    sa.Column('before_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('after_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('changed_fields', postgresql.ARRAY(sa.Text()), nullable=True),
    sa.Column('ip_address', postgresql.INET(), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('request_id', sa.UUID(), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_actor', 'audit_logs', ['actor_id'], unique=False)
    op.create_index('idx_audit_created', 'audit_logs', [sa.text('created_at DESC')], unique=False)
    op.create_index('idx_audit_entity', 'audit_logs', ['entity_type', 'entity_id'], unique=False)
    op.create_index('idx_audit_tenant', 'audit_logs', ['tenant_id'], unique=False)

    # 7. budgets
    op.create_table('budgets',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('fiscal_year', sa.Integer(), nullable=False),
    sa.Column('quarter', sa.Integer(), nullable=False),
    sa.Column('total_cents', sa.BigInteger(), nullable=False),
    sa.Column('spent_cents', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('quarter IN (1,2,3,4)', name='chk_budget_quarter'),
    sa.CheckConstraint('spent_cents <= total_cents', name='chk_budget_spent'),
    sa.CheckConstraint('total_cents > 0', name='chk_budget_positive'),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'department_id', 'fiscal_year', 'quarter', name='uq_budget_tenant_dept_year_quarter')
    )
    op.create_index('idx_budgets_dept', 'budgets', ['department_id', 'fiscal_year'], unique=False)

    # 8. vendors
    op.create_table('vendors',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('legal_name', sa.String(length=200), nullable=False),
    sa.Column('tax_id', sa.String(length=50), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('risk_score', sa.Integer(), nullable=True),
    sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=True),
    sa.Column('bank_account_number_encrypted', sa.Text(), nullable=True),
    sa.Column('bank_name', sa.String(length=200), nullable=True),
    sa.Column('ifsc_code', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_vendors_email', 'vendors', ['email'], unique=False)
    op.create_index('idx_vendors_status', 'vendors', ['status'], unique=False)
    op.create_index('idx_vendors_tenant', 'vendors', ['tenant_id'], unique=False)

    # 9. purchase_requests
    op.create_table('purchase_requests',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('pr_number', sa.String(length=50), nullable=False),
    sa.Column('requester_id', sa.UUID(), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('total_cents', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('justification', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(), nullable=True),
    sa.Column('approved_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('pr_number')
    )
    op.create_index('idx_pr_requester', 'purchase_requests', ['requester_id'], unique=False)
    op.create_index('idx_pr_status', 'purchase_requests', ['status'], unique=False)
    op.create_index('idx_pr_tenant', 'purchase_requests', ['tenant_id'], unique=False)

    # 10. user_devices
    op.create_table('user_devices',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('fcm_token', sa.String(length=500), nullable=False),
    sa.Column('device_type', sa.String(length=10), nullable=False),
    sa.Column('device_name', sa.String(length=200), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('registered_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("device_type IN ('android', 'ios', 'web')", name='chk_device_type'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'fcm_token', name='uq_user_device_token')
    )
    op.create_index('idx_user_devices_tenant', 'user_devices', ['tenant_id'], unique=False)
    op.create_index('idx_user_devices_user', 'user_devices', ['user_id', 'is_active'], unique=False)

    # 11. budget_reservations
    op.create_table('budget_reservations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('budget_id', sa.UUID(), nullable=False),
    sa.Column('entity_type', sa.String(length=20), nullable=False),
    sa.Column('entity_id', sa.UUID(), nullable=False),
    sa.Column('amount_cents', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('released_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("entity_type IN ('PR', 'PO', 'INVOICE')", name='chk_budget_res_entity_type'),
    sa.CheckConstraint("status IN ('COMMITTED', 'SPENT', 'RELEASED')", name='chk_budget_res_status'),
    sa.CheckConstraint('amount_cents > 0', name='chk_budget_res_amount_positive'),
    sa.ForeignKeyConstraint(['budget_id'], ['budgets.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('entity_type', 'entity_id', name='uq_budget_res_entity')
    )
    op.create_index('idx_budget_res_budget', 'budget_reservations', ['budget_id', 'status'], unique=False)
    op.create_index('idx_budget_res_entity', 'budget_reservations', ['entity_type', 'entity_id'], unique=False)

    # 12. vendor_documents
    op.create_table('vendor_documents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('vendor_id', sa.UUID(), nullable=False),
    sa.Column('document_type', sa.String(length=50), nullable=False),
    sa.Column('file_url', sa.Text(), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=True),
    sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
    sa.Column('expiry_date', sa.Date(), nullable=True),
    sa.Column('uploaded_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_vdocs_vendor', 'vendor_documents', ['vendor_id'], unique=False)

    # 13. purchase_orders
    op.create_table('purchase_orders',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('po_number', sa.String(length=50), nullable=False),
    sa.Column('pr_id', sa.UUID(), nullable=True),
    sa.Column('vendor_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('total_cents', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('expected_delivery_date', sa.Date(), nullable=True),
    sa.Column('terms_and_conditions', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['pr_id'], ['purchase_requests.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('po_number')
    )
    op.create_index('idx_po_status', 'purchase_orders', ['status'], unique=False)
    op.create_index('idx_po_tenant', 'purchase_orders', ['tenant_id'], unique=False)
    op.create_index('idx_po_vendor', 'purchase_orders', ['vendor_id'], unique=False)

    # 14. rfqs
    op.create_table('rfqs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('rfq_number', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('pr_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('deadline', sa.DateTime(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("status IN ('DRAFT','OPEN','CLOSED','AWARDED','CANCELLED')", name='chk_rfq_status'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['pr_id'], ['purchase_requests.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('rfq_number')
    )

    # 15. pr_line_items
    op.create_table('pr_line_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('pr_id', sa.UUID(), nullable=False),
    sa.Column('line_number', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('unit_price_cents', sa.BigInteger(), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('quantity > 0', name='chk_pr_line_qty'),
    sa.CheckConstraint('unit_price_cents > 0', name='chk_pr_line_price'),
    sa.ForeignKeyConstraint(['pr_id'], ['purchase_requests.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('pr_id', 'line_number', name='uq_pr_line_item')
    )
    op.create_index('idx_pr_items_pr', 'pr_line_items', ['pr_id'], unique=False)

    # 16. po_line_items
    op.create_table('po_line_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('po_id', sa.UUID(), nullable=False),
    sa.Column('line_number', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('unit_price_cents', sa.BigInteger(), nullable=False),
    sa.Column('received_quantity', sa.Integer(), nullable=False),
    sa.CheckConstraint('quantity > 0', name='chk_po_line_qty'),
    sa.CheckConstraint('unit_price_cents > 0', name='chk_po_line_price'),
    sa.ForeignKeyConstraint(['po_id'], ['purchase_orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('po_id', 'line_number', name='uq_po_line_item')
    )
    op.create_index('idx_po_items_po', 'po_line_items', ['po_id'], unique=False)

    # 17. invoices
    op.create_table('invoices',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('invoice_number', sa.String(length=100), nullable=False),
    sa.Column('po_id', sa.UUID(), nullable=True),
    sa.Column('vendor_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('invoice_date', sa.Date(), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('total_cents', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('document_url', sa.Text(), nullable=True),
    sa.Column('ocr_status', sa.String(length=50), nullable=True),
    sa.Column('ocr_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('match_status', sa.String(length=50), nullable=True),
    sa.Column('match_exceptions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['po_id'], ['purchase_orders.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'invoice_number', 'vendor_id', name='uq_invoice_vendor')
    )
    op.create_index('idx_invoices_po', 'invoices', ['po_id'], unique=False)
    op.create_index('idx_invoices_status', 'invoices', ['status'], unique=False)
    op.create_index('idx_invoices_tenant', 'invoices', ['tenant_id'], unique=False)

    # 18. receipts
    op.create_table('receipts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('receipt_number', sa.String(length=50), nullable=False),
    sa.Column('po_id', sa.UUID(), nullable=False),
    sa.Column('received_by', sa.UUID(), nullable=False),
    sa.Column('receipt_date', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("status IN ('DRAFT','CONFIRMED','CANCELLED')", name='chk_receipt_status'),
    sa.ForeignKeyConstraint(['po_id'], ['purchase_orders.id'], ),
    sa.ForeignKeyConstraint(['received_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('receipt_number')
    )
    op.create_index('idx_receipts_po', 'receipts', ['po_id'], unique=False)

    # 19. rfq_bids
    op.create_table('rfq_bids',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('rfq_id', sa.UUID(), nullable=False),
    sa.Column('vendor_id', sa.UUID(), nullable=False),
    sa.Column('total_cents', sa.BigInteger(), nullable=False),
    sa.Column('delivery_days', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('score', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('submitted_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['rfq_id'], ['rfqs.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('rfq_id', 'vendor_id', name='uq_rfq_bid_vendor')
    )

    # 20. rfq_line_items
    op.create_table('rfq_line_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('rfq_id', sa.UUID(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('specifications', sa.Text(), nullable=True),
    sa.CheckConstraint('quantity > 0', name='chk_rfq_line_qty'),
    sa.ForeignKeyConstraint(['rfq_id'], ['rfqs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # 21. invoice_line_items
    op.create_table('invoice_line_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('invoice_id', sa.UUID(), nullable=False),
    sa.Column('line_number', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('unit_price_cents', sa.BigInteger(), nullable=False),
    sa.CheckConstraint('quantity > 0', name='chk_inv_line_qty'),
    sa.CheckConstraint('unit_price_cents > 0', name='chk_inv_line_price'),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('invoice_id', 'line_number', name='uq_invoice_line_item')
    )

    # 22. payments
    op.create_table('payments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('invoice_id', sa.UUID(), nullable=False),
    sa.Column('amount_cents', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=True),
    sa.Column('paid_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("status IN ('PENDING','PROCESSING','COMPLETED','FAILED')", name='chk_payment_status'),
    sa.CheckConstraint('amount_cents > 0', name='chk_payment_amount'),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_payments_invoice', 'payments', ['invoice_id'], unique=False)
    op.create_index('idx_payments_status', 'payments', ['status'], unique=False)

    # 23. receipt_line_items
    op.create_table('receipt_line_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('receipt_id', sa.UUID(), nullable=False),
    sa.Column('po_line_item_id', sa.UUID(), nullable=False),
    sa.Column('quantity_received', sa.Integer(), nullable=False),
    sa.Column('condition', sa.String(length=20), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.CheckConstraint("condition IN ('GOOD','DAMAGED','PARTIAL')", name='chk_receipt_line_condition'),
    sa.CheckConstraint('quantity_received > 0', name='chk_receipt_line_qty'),
    sa.ForeignKeyConstraint(['receipt_id'], ['receipts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('receipt_line_items')
    op.drop_index('idx_payments_status', table_name='payments')
    op.drop_index('idx_payments_invoice', table_name='payments')
    op.drop_table('payments')
    op.drop_table('invoice_line_items')
    op.drop_table('rfq_line_items')
    op.drop_table('rfq_bids')
    op.drop_index('idx_receipts_po', table_name='receipts')
    op.drop_table('receipts')
    op.drop_index('idx_invoices_tenant', table_name='invoices')
    op.drop_index('idx_invoices_status', table_name='invoices')
    op.drop_index('idx_invoices_po', table_name='invoices')
    op.drop_table('invoices')
    op.drop_index('idx_po_items_po', table_name='po_line_items')
    op.drop_table('po_line_items')
    op.drop_index('idx_po_vendor', table_name='purchase_orders')
    op.drop_index('idx_po_tenant', table_name='purchase_orders')
    op.drop_index('idx_po_status', table_name='purchase_orders')
    op.drop_table('purchase_orders')
    op.drop_index('idx_vdocs_vendor', table_name='vendor_documents')
    op.drop_table('vendor_documents')
    op.drop_table('rfqs')
    op.drop_index('idx_budget_res_entity', table_name='budget_reservations')
    op.drop_index('idx_budget_res_budget', table_name='budget_reservations')
    op.drop_table('budget_reservations')
    op.drop_index('idx_pr_items_pr', table_name='pr_line_items')
    op.drop_table('pr_line_items')
    op.drop_index('idx_pr_tenant', table_name='purchase_requests')
    op.drop_index('idx_pr_status', table_name='purchase_requests')
    op.drop_index('idx_pr_requester', table_name='purchase_requests')
    op.drop_table('purchase_requests')
    op.drop_index('idx_user_devices_user', table_name='user_devices')
    op.drop_index('idx_user_devices_tenant', table_name='user_devices')
    op.drop_table('user_devices')
    op.drop_index('idx_budgets_dept', table_name='budgets')
    op.drop_table('budgets')
    op.drop_index('idx_audit_tenant', table_name='audit_logs')
    op.drop_index('idx_audit_entity', table_name='audit_logs')
    op.drop_index('idx_audit_created', table_name='audit_logs')
    op.drop_index('idx_audit_actor', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index('idx_approvals_entity', table_name='approvals')
    op.drop_index('idx_approvals_approver', table_name='approvals')
    op.drop_table('approvals')
    op.drop_index('idx_vendors_tenant', table_name='vendors')
    op.drop_index('idx_vendors_status', table_name='vendors')
    op.drop_index('idx_vendors_email', table_name='vendors')
    op.drop_table('vendors')
    op.drop_constraint('fk_departments_manager_id', 'departments', type_='foreignkey')
    op.drop_index('idx_users_tenant', table_name='users')
    op.drop_index('idx_users_role', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
    op.drop_table('departments')
    op.drop_index('idx_tenants_status', table_name='tenants')
    op.drop_index('idx_tenants_slug', table_name='tenants')
    op.drop_table('tenants')
