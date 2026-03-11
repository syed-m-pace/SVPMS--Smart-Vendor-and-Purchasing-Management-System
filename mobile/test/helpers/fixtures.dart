import 'package:svpms_vendor/data/models/user.dart';
import 'package:svpms_vendor/data/models/dashboard_stats.dart';
import 'package:svpms_vendor/data/models/purchase_order.dart';
import 'package:svpms_vendor/data/models/invoice.dart';
import 'package:svpms_vendor/data/models/rfq.dart';
import 'package:svpms_vendor/data/models/contract.dart';

User makeUser({
  String id = 'u-001',
  String email = 'vendor@test.com',
  String role = 'vendor',
  String firstName = 'Test',
  String lastName = 'Vendor',
  bool isActive = true,
}) {
  return User(
    id: id,
    email: email,
    role: role,
    firstName: firstName,
    lastName: lastName,
    isActive: isActive,
  );
}

DashboardStats makeDashboardStats({
  int pendingPRs = 3,
  int activePOs = 5,
  int pendingRFQs = 2,
  int openInvoices = 4,
  int budgetUtilization = 67,
}) {
  return DashboardStats(
    pendingPRs: pendingPRs,
    activePOs: activePOs,
    pendingRFQs: pendingRFQs,
    openInvoices: openInvoices,
    budgetUtilization: budgetUtilization,
  );
}

PurchaseOrder makePurchaseOrder({
  String id = 'po-001',
  String poNumber = 'PO-2026-001',
  String status = 'ISSUED',
  int totalCents = 500000,
  String? vendorName = 'Alpha Supplies',
}) {
  return PurchaseOrder(
    id: id,
    poNumber: poNumber,
    status: status,
    totalCents: totalCents,
    vendorName: vendorName,
    lineItems: [
      const POLineItem(
        id: 'li-001',
        description: 'Office Chairs',
        quantity: 10,
        unitPriceCents: 50000,
      ),
    ],
  );
}

Invoice makeInvoice({
  String id = 'inv-001',
  String invoiceNumber = 'INV-2026-001',
  String status = 'UPLOADED',
  int totalCents = 500000,
  String? poId = 'po-001',
  String? poNumber = 'PO-2026-001',
}) {
  return Invoice(
    id: id,
    invoiceNumber: invoiceNumber,
    status: status,
    totalCents: totalCents,
    poId: poId,
    poNumber: poNumber,
  );
}

RFQ makeRFQ({
  String id = 'rfq-001',
  String rfqNumber = 'RFQ-2026-001',
  String title = 'Office Furniture',
  String status = 'OPEN',
}) {
  return RFQ(
    id: id,
    rfqNumber: rfqNumber,
    title: title,
    status: status,
    lineItems: [
      const RFQLineItem(
        id: 'rli-001',
        description: 'Ergonomic Chairs',
        quantity: 20,
        unit: 'pieces',
      ),
    ],
    bids: [
      const RFQBid(
        id: 'bid-001',
        vendorId: 'v-001',
        totalCents: 1000000,
        deliveryDays: 14,
      ),
    ],
  );
}

Contract makeContract({
  String id = 'c-001',
  String contractNumber = 'CON-2026-001',
  String title = 'Annual Supply Agreement',
  String status = 'ACTIVE',
  int? valueCents = 10000000,
}) {
  return Contract(
    id: id,
    contractNumber: contractNumber,
    title: title,
    status: status,
    valueCents: valueCents,
    startDate: '2026-01-01',
    endDate: '2026-12-31',
  );
}

/// Generate a list of N items using a factory function.
List<T> makeList<T>(int count, T Function(int index) factory) {
  return List.generate(count, factory);
}

// ─── Raw JSON factories (matching API response shape) ───

Map<String, dynamic> makeUserJson({
  String id = 'u-001',
  String email = 'vendor@test.com',
  String role = 'vendor',
  String firstName = 'Test',
  String lastName = 'Vendor',
  bool isActive = true,
}) =>
    {
      'id': id,
      'email': email,
      'role': role,
      'first_name': firstName,
      'last_name': lastName,
      'is_active': isActive,
      'department_id': null,
      'profile_photo_url': null,
    };

Map<String, dynamic> makeDashboardStatsJson({
  int pendingPRs = 3,
  int activePOs = 5,
  int pendingRFQs = 2,
  int openInvoices = 4,
  int budgetUtilization = 67,
}) =>
    {
      'pending_prs': pendingPRs,
      'active_pos': activePOs,
      'pending_rfqs': pendingRFQs,
      'open_invoices': openInvoices,
      'budget_utilization': budgetUtilization,
    };

Map<String, dynamic> makePurchaseOrderJson({
  String id = 'po-001',
  String poNumber = 'PO-2026-001',
  String status = 'ISSUED',
  int totalCents = 500000,
  String? vendorName = 'Alpha Supplies',
  List<Map<String, dynamic>>? lineItems,
}) =>
    {
      'id': id,
      'po_number': poNumber,
      'status': status,
      'total_cents': totalCents,
      'currency': 'INR',
      'vendor_id': 'v-001',
      'vendor_name': vendorName,
      'issued_at': '2026-01-15T10:00:00Z',
      'expected_delivery_date': '2026-02-15',
      'created_at': '2026-01-15T10:00:00Z',
      'line_items': lineItems ??
          [
            {
              'id': 'li-001',
              'description': 'Office Chairs',
              'quantity': 10,
              'unit_price_cents': 50000,
            },
          ],
    };

Map<String, dynamic> makeInvoiceJson({
  String id = 'inv-001',
  String invoiceNumber = 'INV-2026-001',
  String status = 'UPLOADED',
  int totalCents = 500000,
  String? poId = 'po-001',
  String? poNumber = 'PO-2026-001',
}) =>
    {
      'id': id,
      'invoice_number': invoiceNumber,
      'status': status,
      'total_cents': totalCents,
      'currency': 'INR',
      'po_id': poId,
      'po_number': poNumber,
      'match_status': null,
      'invoice_date': '2026-01-20',
      'created_at': '2026-01-20T10:00:00Z',
      'document_url': null,
      'ocr_status': null,
      'vendor_name': 'Alpha Supplies',
      'match_exceptions': null,
    };

Map<String, dynamic> makeRFQJson({
  String id = 'rfq-001',
  String rfqNumber = 'RFQ-2026-001',
  String title = 'Office Furniture',
  String status = 'OPEN',
  List<Map<String, dynamic>>? lineItems,
  List<Map<String, dynamic>>? bids,
}) =>
    {
      'id': id,
      'rfq_number': rfqNumber,
      'title': title,
      'description': 'Procurement of office furniture',
      'status': status,
      'deadline': '2026-02-28T23:59:59Z',
      'created_at': '2026-01-10T10:00:00Z',
      'budget_cents': 2000000,
      'awarded_vendor_id': null,
      'awarded_po_id': null,
      'line_items': lineItems ??
          [
            {
              'id': 'rli-001',
              'description': 'Ergonomic Chairs',
              'quantity': 20,
              'unit': 'pieces',
            },
          ],
      'bids': bids ??
          [
            {
              'id': 'bid-001',
              'vendor_id': 'v-001',
              'total_cents': 1000000,
              'delivery_days': 14,
              'notes': null,
            },
          ],
    };

Map<String, dynamic> makeContractJson({
  String id = 'c-001',
  String contractNumber = 'CON-2026-001',
  String title = 'Annual Supply Agreement',
  String status = 'ACTIVE',
  int? valueCents = 10000000,
}) =>
    {
      'id': id,
      'contract_number': contractNumber,
      'title': title,
      'status': status,
      'description': 'Annual office supplies agreement',
      'value_cents': valueCents,
      'currency': 'INR',
      'start_date': '2026-01-01',
      'end_date': '2026-12-31',
      'auto_renew': false,
      'renewal_notice_days': 30,
      'sla_terms': '99.9% uptime',
      'vendor_name': 'Alpha Supplies',
      'terminated_at': null,
      'created_at': '2026-01-01T00:00:00Z',
    };
