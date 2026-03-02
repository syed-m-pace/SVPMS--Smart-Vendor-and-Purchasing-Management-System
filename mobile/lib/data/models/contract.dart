class Contract {
  final String id;
  final String contractNumber;
  final String title;
  final String status;
  final String? description;
  final int? valueCents;
  final String currency;
  final String startDate;
  final String endDate;
  final bool autoRenew;
  final int renewalNoticeDays;
  final String? slaTerms;
  final String? vendorName;
  final String? terminatedAt;
  final String? createdAt;

  const Contract({
    required this.id,
    required this.contractNumber,
    required this.title,
    required this.status,
    this.description,
    this.valueCents,
    this.currency = 'INR',
    required this.startDate,
    required this.endDate,
    this.autoRenew = false,
    this.renewalNoticeDays = 30,
    this.slaTerms,
    this.vendorName,
    this.terminatedAt,
    this.createdAt,
  });

  factory Contract.fromJson(Map<String, dynamic> json) {
    return Contract(
      id: json['id'] ?? '',
      contractNumber: json['contract_number'] ?? json['contractNumber'] ?? '',
      title: json['title'] ?? '',
      status: json['status'] ?? '',
      description: json['description'],
      valueCents: json['value_cents'] ?? json['valueCents'],
      currency: json['currency'] ?? 'INR',
      startDate: json['start_date'] ?? json['startDate'] ?? '',
      endDate: json['end_date'] ?? json['endDate'] ?? '',
      autoRenew: json['auto_renew'] ?? json['autoRenew'] ?? false,
      renewalNoticeDays: json['renewal_notice_days'] ?? json['renewalNoticeDays'] ?? 30,
      slaTerms: json['sla_terms'] ?? json['slaTerms'],
      vendorName: json['vendor_name'] ?? json['vendorName'],
      terminatedAt: json['terminated_at'] ?? json['terminatedAt'],
      createdAt: json['created_at'] ?? json['createdAt'],
    );
  }
}
