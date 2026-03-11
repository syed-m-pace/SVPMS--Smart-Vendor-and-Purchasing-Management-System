import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/data/models/rfq.dart';
import '../../helpers/fixtures.dart';

void main() {
  group('RFQ.fromJson', () {
    test('parses all fields with line items and bids', () {
      final json = makeRFQJson();
      final rfq = RFQ.fromJson(json);
      expect(rfq.id, 'rfq-001');
      expect(rfq.rfqNumber, 'RFQ-2026-001');
      expect(rfq.title, 'Office Furniture');
      expect(rfq.status, 'OPEN');
      expect(rfq.budgetCents, 2000000);
      expect(rfq.lineItems.length, 1);
      expect(rfq.bids.length, 1);
    });

    test('handles empty line items and bids', () {
      final json = makeRFQJson(lineItems: [], bids: []);
      final rfq = RFQ.fromJson(json);
      expect(rfq.lineItems, isEmpty);
      expect(rfq.bids, isEmpty);
    });

    test('handles null line_items and bids keys', () {
      final json = makeRFQJson();
      json.remove('line_items');
      json.remove('bids');
      final rfq = RFQ.fromJson(json);
      expect(rfq.lineItems, isEmpty);
      expect(rfq.bids, isEmpty);
    });
  });

  group('RFQLineItem.fromJson', () {
    test('parses all fields', () {
      final json = {
        'id': 'rli-1',
        'description': 'Monitors',
        'quantity': 15,
        'unit': 'pieces',
      };
      final item = RFQLineItem.fromJson(json);
      expect(item.id, 'rli-1');
      expect(item.description, 'Monitors');
      expect(item.quantity, 15.0);
      expect(item.unit, 'pieces');
    });
  });

  group('RFQBid.fromJson', () {
    test('parses all fields', () {
      final json = {
        'id': 'bid-1',
        'vendor_id': 'v-001',
        'total_cents': 500000,
        'delivery_days': 7,
        'notes': 'Fast delivery',
      };
      final bid = RFQBid.fromJson(json);
      expect(bid.id, 'bid-1');
      expect(bid.vendorId, 'v-001');
      expect(bid.totalCents, 500000);
      expect(bid.deliveryDays, 7);
      expect(bid.notes, 'Fast delivery');
    });

    test('handles null optional fields', () {
      final json = {
        'id': 'bid-2',
        'vendor_id': 'v-002',
        'total_cents': 300000,
      };
      final bid = RFQBid.fromJson(json);
      expect(bid.deliveryDays, isNull);
      expect(bid.notes, isNull);
    });
  });
}
