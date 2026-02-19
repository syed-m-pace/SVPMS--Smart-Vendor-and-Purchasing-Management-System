import '../datasources/api/api_client.dart';
import '../models/invoice.dart';

class InvoiceRepository {
  final ApiClient _api;

  InvoiceRepository({required ApiClient api}) : _api = api;

  Future<List<Invoice>> list({String? status, int page = 1}) async {
    final data = await _api.getInvoices(status: status, page: page);
    final items = data['items'] as List<dynamic>? ?? [];
    return items
        .map((e) => Invoice.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Invoice> upload({
    required String poId,
    required String invoiceNumber,
    required String invoiceDate,
    required int totalCents,
    String? filePath,
  }) async {
    String? documentUrl;
    if (filePath != null) {
      final fileData = await _api.uploadFile(filePath);
      // We store the presigned URL or key. Using presigned_url for immediate access/OCR.
      // Ideally, the backend would take the key, but we fit the 'document_url' field.
      documentUrl = fileData['presigned_url'];
    }

    final data = await _api.createInvoice(
      poId: poId,
      invoiceNumber: invoiceNumber,
      invoiceDate: invoiceDate,
      totalCents: totalCents,
      documentUrl: documentUrl,
    );
    return Invoice.fromJson(data);
  }
}
