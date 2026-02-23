class Invoice {
  final String id;
  final String invoiceNumber;
  final String status;
  final int totalCents;
  final String currency;
  final String? poId;
  final String? poNumber;
  final String? matchStatus;
  final String? invoiceDate;
  final String? createdAt;
  final String? documentUrl;
  final String? ocrStatus;
  final String? vendorName;

  const Invoice({
    required this.id,
    required this.invoiceNumber,
    required this.status,
    required this.totalCents,
    this.currency = 'INR',
    this.poId,
    this.poNumber,
    this.matchStatus,
    this.invoiceDate,
    this.createdAt,
    this.documentUrl,
    this.ocrStatus,
    this.vendorName,
  });

  factory Invoice.fromJson(Map<String, dynamic> json) {
    return Invoice(
      id: json['id'] ?? '',
      invoiceNumber: json['invoice_number'] ?? json['invoiceNumber'] ?? '',
      status: json['status'] ?? '',
      totalCents: json['total_cents'] ?? json['totalCents'] ?? 0,
      currency: json['currency'] ?? 'INR',
      poId: json['po_id'],
      poNumber: json['po_number'],
      matchStatus: json['match_status'],
      invoiceDate: json['invoice_date'],
      createdAt: json['created_at'],
      documentUrl: json['document_url'],
      ocrStatus: json['ocr_status'],
      vendorName: json['vendor_name'],
    );
  }
}
