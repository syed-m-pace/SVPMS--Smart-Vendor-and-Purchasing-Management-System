import '../datasources/api/api_client.dart';
import '../models/invoice.dart';

class InvoiceRepository {
  final ApiClient _api;

  InvoiceRepository({required ApiClient api}) : _api = api;

  Future<Invoice> get(String id) async {
    final data = await _api.getInvoice(id);
    return Invoice.fromJson(data);
  }

  Future<String> getPresignedUrl(String fileKey) async {
    final data = await _api.getFilePresignedUrl(fileKey);
    return data['presigned_url'] as String;
  }

  Future<List<Invoice>> list({String? status, int page = 1}) async {
    final data = await _api.getInvoices(status: status, page: page);
    final items =
        data['data'] as List<dynamic>? ?? data['items'] as List<dynamic>? ?? [];
    return items
        .map((e) => Invoice.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Invoice> disputeInvoice(String id, {String? reason}) async {
    final data = await _api.disputeInvoice(id, reason: reason);
    return Invoice.fromJson(data);
  }

  Future<Invoice> reuploadInvoice(String id, String filePath) async {
    final fileData = await _api.uploadFile(filePath);
    final documentKey = fileData['file_key'];
    final data = await _api.reuploadInvoice(id, documentKey);
    return Invoice.fromJson(data);
  }

  Future<Invoice> upload({
    required String poId,
    required String invoiceNumber,
    required String invoiceDate,
    required int totalCents,
    String? filePath,
  }) async {
    String? documentKey;
    if (filePath != null) {
      final fileData = await _api.uploadFile(filePath);
      documentKey = fileData['file_key'];
    }

    final data = await _api.createInvoice(
      poId: poId,
      invoiceNumber: invoiceNumber,
      invoiceDate: invoiceDate,
      totalCents: totalCents,
      documentKey: documentKey,
    );
    return Invoice.fromJson(data);
  }
}
