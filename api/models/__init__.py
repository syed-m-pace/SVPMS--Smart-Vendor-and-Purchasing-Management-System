"""Central model registry — import all models so Alembic autodiscover works."""

from api.database import Base  # noqa: F401

from api.models.tenant import Tenant  # noqa: F401
from api.models.user import User  # noqa: F401
from api.models.department import Department  # noqa: F401
from api.models.budget import Budget, BudgetReservation  # noqa: F401
from api.models.vendor import Vendor, VendorDocument  # noqa: F401
from api.models.purchase_request import PurchaseRequest, PrLineItem  # noqa: F401
from api.models.purchase_order import PurchaseOrder, PoLineItem  # noqa: F401
from api.models.receipt import Receipt, ReceiptLineItem  # noqa: F401
from api.models.invoice import Invoice, InvoiceLineItem  # noqa: F401
from api.models.approval import Approval  # noqa: F401
from api.models.audit_log import AuditLog  # noqa: F401
from api.models.rfq import Rfq, RfqLineItem, RfqBid  # noqa: F401
from api.models.payment import Payment  # noqa: F401
from api.models.user_device import UserDevice  # noqa: F401
