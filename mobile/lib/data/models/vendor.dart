class Vendor {
  final String id;
  final String legalName;
  final String email;
  final String? contactPerson;
  final String? gstNumber;
  final String? bankAccount; // Masked from backend ideally
  final String status;

  const Vendor({
    required this.id,
    required this.legalName,
    required this.email,
    this.contactPerson,
    this.gstNumber,
    this.bankAccount,
    this.status = 'ACTIVE',
  });

  factory Vendor.fromJson(Map<String, dynamic> json) {
    return Vendor(
      id: json['id'] ?? '',
      legalName: json['legal_name'] ?? json['legalName'] ?? '',
      email: json['email'] ?? '',
      contactPerson: json['contact_person'] ?? json['contactPerson'],
      gstNumber: json['gst_number'] ?? json['gstNumber'],
      bankAccount: json['bank_account'] ?? json['bankAccount'],
      status: json['status'] ?? 'ACTIVE',
    );
  }
}
