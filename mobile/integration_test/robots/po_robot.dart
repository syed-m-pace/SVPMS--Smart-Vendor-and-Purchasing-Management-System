import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class PORobot {
  final WidgetTester tester;

  PORobot(this.tester);

  // Finders
  final poListTile = find.byType(ListTile);
  final acknowledgeButton = find.text('Acknowledge Order');
  final acknowledgedStatus = find.text('ACKNOWLEDGED');

  Future<void> openFirstPO() async {
    await tester.tap(poListTile.first);
    await tester.pumpAndSettle();
  }

  Future<void> acknowledgePO() async {
    await tester.tap(acknowledgeButton);
    await tester.pumpAndSettle();
  }

  Future<void> verifyPOAcknowledged() async {
    expect(acknowledgedStatus, findsOneWidget);
  }
}
