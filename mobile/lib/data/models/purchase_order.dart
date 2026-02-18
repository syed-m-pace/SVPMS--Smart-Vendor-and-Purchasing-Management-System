class PurchaseOrder {
  final String id;
  final String poNumber;
  final String status;
  final int totalCents;
  final String currency;
  final String? vendorId;
  final String? vendorName;
  final String? issuedAt;
  final String? expectedDeliveryDate;
  final String? createdAt;
  final List<POLineItem> lineItems;

  const PurchaseOrder({
    required this.id,
    required this.poNumber,
    required this.status,
    required this.totalCents,
    this.currency = 'INR',
    this.vendorId,
    this.vendorName,
    this.issuedAt,
    this.expectedDeliveryDate,
    this.createdAt,
    this.lineItems = const [],
  });

  factory PurchaseOrder.fromJson(Map<String, dynamic> json) {
    return PurchaseOrder(
      id: json['id'] ?? '',
      poNumber: json['po_number'] ?? json['poNumber'] ?? '',
      status: json['status'] ?? '',
      totalCents: json['total_cents'] ?? json['totalCents'] ?? 0,
      currency: json['currency'] ?? 'INR',
      vendorId: json['vendor_id'],
      vendorName: json['vendor_name'],
      issuedAt: json['issued_at'],
      expectedDeliveryDate: json['expected_delivery_date'],
      createdAt: json['created_at'],
      lineItems:
          (json['line_items'] as List<dynamic>?)
              ?.map((e) => POLineItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}

class POLineItem {
  final String id;
  final String description;
  final double quantity;
  final int unitPriceCents;

  const POLineItem({
    required this.id,
    required this.description,
    required this.quantity,
    required this.unitPriceCents,
  });

  factory POLineItem.fromJson(Map<String, dynamic> json) {
    return POLineItem(
      id: json['id'] ?? '',
      description: json['description'] ?? '',
      quantity: (json['quantity'] ?? 0).toDouble(),
      unitPriceCents: json['unit_price_cents'] ?? json['unitPriceCents'] ?? 0,
    );
  }
}
