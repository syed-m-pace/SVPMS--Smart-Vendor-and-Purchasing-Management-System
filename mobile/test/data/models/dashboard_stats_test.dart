import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/data/models/dashboard_stats.dart';
import '../../helpers/fixtures.dart';

void main() {
  group('DashboardStats.fromJson', () {
    test('parses snake_case keys', () {
      final json = makeDashboardStatsJson();
      final stats = DashboardStats.fromJson(json);
      expect(stats.pendingPRs, 3);
      expect(stats.activePOs, 5);
      expect(stats.pendingRFQs, 2);
      expect(stats.openInvoices, 4);
      expect(stats.budgetUtilization, 67);
    });

    test('parses camelCase keys', () {
      final json = {
        'pendingPRs': 10,
        'activePOs': 20,
        'pendingRFQs': 5,
        'openInvoices': 8,
        'budgetUtilization': 90,
      };
      final stats = DashboardStats.fromJson(json);
      expect(stats.pendingPRs, 10);
      expect(stats.activePOs, 20);
      expect(stats.pendingRFQs, 5);
      expect(stats.openInvoices, 8);
      expect(stats.budgetUtilization, 90);
    });

    test('defaults to 0 when keys missing', () {
      final stats = DashboardStats.fromJson({});
      expect(stats.pendingPRs, 0);
      expect(stats.activePOs, 0);
      expect(stats.pendingRFQs, 0);
      expect(stats.openInvoices, 0);
      expect(stats.budgetUtilization, 0);
    });
  });
}
