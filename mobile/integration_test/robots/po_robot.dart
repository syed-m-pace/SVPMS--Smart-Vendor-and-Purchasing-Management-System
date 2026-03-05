import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class PORobot {
  final WidgetTester tester;

  PORobot(this.tester);

  // Key-based finders
  Finder poItem(String poId) => find.byKey(Key('po_item_$poId'));
  final acknowledgeButton = find.text('Acknowledge Order');
  final acknowledgedStatus = find.text('ACKNOWLEDGED');

  Future<void> verifyPOListLoaded() async {
    await tester.pumpAndSettle(const Duration(seconds: 5));
    // At least one PO item should be visible
    expect(find.byKey(const Key('po_item_po-001')), findsOneWidget);
  }

  Future<void> openPO(String poId) async {
    final item = poItem(poId);
    expect(item, findsOneWidget);
    await tester.tap(item);
    await tester.pumpAndSettle(const Duration(seconds: 5));
  }

  Future<void> acknowledgePO() async {
    expect(acknowledgeButton, findsOneWidget);
    await tester.tap(acknowledgeButton);
    await tester.pumpAndSettle(const Duration(seconds: 5));
  }

  Future<void> verifyPOAcknowledged() async {
    expect(acknowledgedStatus, findsOneWidget);
  }
}
