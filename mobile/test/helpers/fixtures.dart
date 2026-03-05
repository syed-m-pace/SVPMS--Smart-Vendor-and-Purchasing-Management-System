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
