import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class DashboardRobot {
  final WidgetTester tester;

  DashboardRobot(this.tester);

  // Key-based finders
  final activePOsStat = find.byKey(const Key('dashboard_stat_active_pos'));
  final pendingRFQsStat = find.byKey(const Key('dashboard_stat_pending_rfqs'));
  final openInvoicesStat = find.byKey(const Key('dashboard_stat_open_invoices'));
  final recentPOsHeader = find.byKey(const Key('dashboard_recent_pos_header'));
  final bottomNavOrders = find.byIcon(Icons.shopping_cart_outlined);
  final bottomNavInvoices = find.byIcon(Icons.receipt_long_outlined);

  Future<void> verifyDashboardLoaded() async {
    await tester.pumpAndSettle(const Duration(seconds: 5));
    expect(activePOsStat, findsOneWidget);
    expect(pendingRFQsStat, findsOneWidget);
    expect(openInvoicesStat, findsOneWidget);
  }

  Future<void> navigateToOrders() async {
    await tester.tap(bottomNavOrders);
    await tester.pumpAndSettle(const Duration(seconds: 5));
  }

  Future<void> navigateToInvoices() async {
    await tester.tap(bottomNavInvoices);
    await tester.pumpAndSettle(const Duration(seconds: 5));
  }
}
