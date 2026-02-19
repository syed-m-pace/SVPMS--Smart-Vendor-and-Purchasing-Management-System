import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class DashboardRobot {
  final WidgetTester tester;

  DashboardRobot(this.tester);

  // Finders
  final pendingPOCard = find.text('Pending POs');
  final activeRFQCard = find.text('Active RFQs');
  final bottomNavOrders = find.byIcon(Icons.shopping_cart_outlined);
  final bottomNavInvoices = find.byIcon(Icons.receipt_long_outlined);

  Future<void> verifyDashboardLoaded() async {
    await tester.pumpAndSettle();
    expect(pendingPOCard, findsOneWidget);
    expect(activeRFQCard, findsOneWidget);
  }

  Future<void> navigateToOrders() async {
    await tester.tap(bottomNavOrders);
    await tester.pumpAndSettle();
  }

  Future<void> navigateToInvoices() async {
    await tester.tap(bottomNavInvoices);
    await tester.pumpAndSettle();
  }
}
