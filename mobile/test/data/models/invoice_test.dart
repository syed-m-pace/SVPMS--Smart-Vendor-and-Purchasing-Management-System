import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/data/models/invoice.dart';
import '../../helpers/fixtures.dart';

void main() {
  group('Invoice.fromJson', () {
    test('parses all fields correctly', () {
      final json = makeInvoiceJson();
      final inv = Invoice.fromJson(json);
      expect(inv.id, 'inv-001');
      expect(inv.invoiceNumber, 'INV-2026-001');
      expect(inv.status, 'UPLOADED');
      expect(inv.totalCents, 500000);
      expect(inv.currency, 'INR');
      expect(inv.poId, 'po-001');
      expect(inv.poNumber, 'PO-2026-001');
      expect(inv.vendorName, 'Alpha Supplies');
      expect(inv.matchExceptions, isNull);
    });

    test('handles null optional fields', () {
      final json = {
        'id': 'inv-002',
        'invoice_number': 'INV-002',
        'status': 'MATCHED',
        'total_cents': 100,
      };
      final inv = Invoice.fromJson(json);
      expect(inv.poId, isNull);
      expect(inv.poNumber, isNull);
      expect(inv.documentUrl, isNull);
      expect(inv.ocrStatus, isNull);
    });

    test('parses match_exceptions map', () {
      final json = makeInvoiceJson();
      json['match_exceptions'] = {'amount_mismatch': true, 'quantity_diff': 5};
      final inv = Invoice.fromJson(json);
      expect(inv.matchExceptions, isA<Map<String, dynamic>>());
      expect(inv.matchExceptions!['amount_mismatch'], true);
    });

    test('defaults to empty string / 0 for missing required keys', () {
      final inv = Invoice.fromJson({});
      expect(inv.id, '');
      expect(inv.invoiceNumber, '');
      expect(inv.status, '');
      expect(inv.totalCents, 0);
    });
  });
}
