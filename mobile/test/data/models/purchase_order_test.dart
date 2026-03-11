import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/data/models/purchase_order.dart';
import '../../helpers/fixtures.dart';

void main() {
  group('PurchaseOrder.fromJson', () {
    test('parses all fields with line items', () {
      final json = makePurchaseOrderJson();
      final po = PurchaseOrder.fromJson(json);
      expect(po.id, 'po-001');
      expect(po.poNumber, 'PO-2026-001');
      expect(po.status, 'ISSUED');
      expect(po.totalCents, 500000);
      expect(po.currency, 'INR');
      expect(po.vendorName, 'Alpha Supplies');
      expect(po.lineItems.length, 1);
      expect(po.lineItems.first.description, 'Office Chairs');
      expect(po.lineItems.first.quantity, 10.0);
      expect(po.lineItems.first.unitPriceCents, 50000);
    });

    test('handles empty line items', () {
      final json = makePurchaseOrderJson(lineItems: []);
      final po = PurchaseOrder.fromJson(json);
      expect(po.lineItems, isEmpty);
    });

    test('handles null line items', () {
      final json = makePurchaseOrderJson();
      json.remove('line_items');
      final po = PurchaseOrder.fromJson(json);
      expect(po.lineItems, isEmpty);
    });

    test('defaults to empty string / 0 for missing keys', () {
      final po = PurchaseOrder.fromJson({});
      expect(po.id, '');
      expect(po.poNumber, '');
      expect(po.status, '');
      expect(po.totalCents, 0);
      expect(po.currency, 'INR');
    });
  });

  group('POLineItem.fromJson', () {
    test('parses snake_case keys', () {
      final json = {
        'id': 'li-1',
        'description': 'Desks',
        'quantity': 5,
        'unit_price_cents': 100000,
      };
      final item = POLineItem.fromJson(json);
      expect(item.id, 'li-1');
      expect(item.description, 'Desks');
      expect(item.quantity, 5.0);
      expect(item.unitPriceCents, 100000);
    });
  });
}
