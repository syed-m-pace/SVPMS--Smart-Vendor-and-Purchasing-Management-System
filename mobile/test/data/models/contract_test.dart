import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/data/models/contract.dart';
import '../../helpers/fixtures.dart';

void main() {
  group('Contract.fromJson', () {
    test('parses all fields correctly', () {
      final json = makeContractJson();
      final c = Contract.fromJson(json);
      expect(c.id, 'c-001');
      expect(c.contractNumber, 'CON-2026-001');
      expect(c.title, 'Annual Supply Agreement');
      expect(c.status, 'ACTIVE');
      expect(c.valueCents, 10000000);
      expect(c.currency, 'INR');
      expect(c.startDate, '2026-01-01');
      expect(c.endDate, '2026-12-31');
      expect(c.autoRenew, false);
      expect(c.renewalNoticeDays, 30);
      expect(c.slaTerms, '99.9% uptime');
      expect(c.vendorName, 'Alpha Supplies');
    });

    test('handles camelCase keys', () {
      final json = {
        'id': 'c-002',
        'contractNumber': 'CON-002',
        'title': 'Test',
        'status': 'DRAFT',
        'startDate': '2026-06-01',
        'endDate': '2027-06-01',
        'autoRenew': true,
        'renewalNoticeDays': 60,
        'slaTerms': 'Standard SLA',
        'vendorName': 'Beta Corp',
        'valueCents': 5000000,
      };
      final c = Contract.fromJson(json);
      expect(c.contractNumber, 'CON-002');
      expect(c.autoRenew, true);
      expect(c.renewalNoticeDays, 60);
      expect(c.slaTerms, 'Standard SLA');
      expect(c.vendorName, 'Beta Corp');
    });

    test('defaults for missing keys', () {
      final c = Contract.fromJson({});
      expect(c.id, '');
      expect(c.contractNumber, '');
      expect(c.title, '');
      expect(c.status, '');
      expect(c.startDate, '');
      expect(c.endDate, '');
      expect(c.autoRenew, false);
      expect(c.renewalNoticeDays, 30);
      expect(c.currency, 'INR');
      expect(c.valueCents, isNull);
    });
  });
}
