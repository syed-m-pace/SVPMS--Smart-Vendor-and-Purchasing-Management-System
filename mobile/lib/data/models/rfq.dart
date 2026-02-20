class RFQ {
  final String id;
  final String rfqNumber;
  final String title;
  final String? description;
  final String status;
  final String? deadline;
  final String? createdAt;
  final int? budgetCents;
  final List<RFQLineItem> lineItems;
  final List<RFQBid> bids;

  const RFQ({
    required this.id,
    required this.rfqNumber,
    required this.title,
    this.description,
    required this.status,
    this.deadline,
    this.createdAt,
    this.budgetCents,
    this.lineItems = const [],
    this.bids = const [],
  });

  factory RFQ.fromJson(Map<String, dynamic> json) {
    return RFQ(
      id: json['id'] ?? '',
      rfqNumber: json['rfq_number'] ?? json['rfqNumber'] ?? '',
      title: json['title'] ?? '',
      description: json['description'],
      status: json['status'] ?? '',
      deadline: json['deadline'],
      createdAt: json['created_at'],
      budgetCents: json['budget_cents'],
      lineItems:
          (json['line_items'] as List<dynamic>?)
              ?.map((e) => RFQLineItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      bids:
          (json['bids'] as List<dynamic>?)
              ?.map((e) => RFQBid.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}

class RFQLineItem {
  final String id;
  final String description;
  final double quantity;
  final String? unit;

  const RFQLineItem({
    required this.id,
    required this.description,
    required this.quantity,
    this.unit,
  });

  factory RFQLineItem.fromJson(Map<String, dynamic> json) {
    return RFQLineItem(
      id: json['id'] ?? '',
      description: json['description'] ?? '',
      quantity: (json['quantity'] ?? 0).toDouble(),
      unit: json['unit'],
    );
  }
}

class RFQBid {
  final String id;
  final String vendorId;
  final int totalCents;
  final int? deliveryDays;
  final String? notes;

  const RFQBid({
    required this.id,
    required this.vendorId,
    required this.totalCents,
    this.deliveryDays,
    this.notes,
  });

  factory RFQBid.fromJson(Map<String, dynamic> json) {
    return RFQBid(
      id: json['id'] ?? '',
      vendorId: json['vendor_id'] ?? '',
      totalCents: json['total_cents'] ?? 0,
      deliveryDays: json['delivery_days'],
      notes: json['notes'],
    );
  }
}
