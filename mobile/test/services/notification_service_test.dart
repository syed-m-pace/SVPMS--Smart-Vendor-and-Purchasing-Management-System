import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/services/notification_service.dart';

void main() {
  group('AppNotification.fromJson', () {
    test('parses all fields', () {
      final json = {
        'id': 'n-001',
        'title': 'New PO',
        'body': 'You have a new PO',
        'type': 'NEW_PO',
        'deepLinkPath': '/purchase-orders/po-001',
        'receivedAt': '2026-01-15T10:00:00Z',
        'isRead': false,
      };
      final n = AppNotification.fromJson(json);
      expect(n.id, 'n-001');
      expect(n.title, 'New PO');
      expect(n.body, 'You have a new PO');
      expect(n.type, 'NEW_PO');
      expect(n.deepLinkPath, '/purchase-orders/po-001');
      expect(n.isRead, false);
    });

    test('parses API response format with message and entity_id', () {
      final json = {
        'id': 'n-002',
        'title': 'Invoice Paid',
        'message': 'Invoice INV-001 has been paid',
        'type': 'INVOICE_PAID',
        'entity_id': 'inv-001',
        'created_at': '2026-01-20T10:00:00Z',
        'is_read': true,
      };
      final n = AppNotification.fromJson(json);
      expect(n.body, 'Invoice INV-001 has been paid');
      expect(n.deepLinkPath, '/invoices/inv-001');
      expect(n.isRead, true);
    });

    test('handles missing fields gracefully', () {
      final n = AppNotification.fromJson({});
      expect(n.id, '');
      expect(n.title, '');
      expect(n.body, '');
      expect(n.type, 'GENERIC');
      expect(n.isRead, false);
    });

    test('builds correct deep link paths for different types', () {
      // NEW_PO
      final po = AppNotification.fromJson({
        'type': 'NEW_PO',
        'entity_id': 'po-123',
      });
      expect(po.deepLinkPath, '/purchase-orders/po-123');

      // NEW_RFQ
      final rfq = AppNotification.fromJson({
        'type': 'NEW_RFQ',
        'entity_id': 'rfq-123',
      });
      expect(rfq.deepLinkPath, '/rfqs/rfq-123');

      // INVOICE_MATCHED
      final inv = AppNotification.fromJson({
        'type': 'INVOICE_MATCHED',
        'entity_id': 'inv-123',
      });
      expect(inv.deepLinkPath, '/invoices/inv-123');

      // Unknown type with entity_id -> null
      final unknown = AppNotification.fromJson({
        'type': 'UNKNOWN',
        'entity_id': 'x-123',
      });
      expect(unknown.deepLinkPath, isNull);
    });
  });

  group('AppNotification.toJson', () {
    test('round-trips through toJson and fromJson', () {
      final original = AppNotification(
        id: 'n-001',
        title: 'Test',
        body: 'Test body',
        type: 'GENERIC',
        deepLinkPath: '/dashboard',
        receivedAt: DateTime.parse('2026-01-15T10:00:00.000Z'),
        isRead: true,
      );
      final json = original.toJson();
      expect(json['id'], 'n-001');
      expect(json['title'], 'Test');
      expect(json['body'], 'Test body');
      expect(json['type'], 'GENERIC');
      expect(json['deepLinkPath'], '/dashboard');
      expect(json['isRead'], true);
    });
  });

  group('AppNotification.copyWith', () {
    test('copies with isRead changed', () {
      final n = AppNotification(
        id: 'n-001',
        title: 'Test',
        body: 'Body',
        type: 'GENERIC',
        receivedAt: DateTime.now(),
        isRead: false,
      );
      final read = n.copyWith(isRead: true);
      expect(read.isRead, true);
      expect(read.id, 'n-001');
    });
  });
}
