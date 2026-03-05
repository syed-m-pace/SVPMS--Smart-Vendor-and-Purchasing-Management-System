import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class InvoiceRobot {
  final WidgetTester tester;

  InvoiceRobot(this.tester);

  // Key-based finders
  Finder invoiceItem(String invoiceId) => find.byKey(Key('invoice_item_$invoiceId'));
  final createInvoiceButton = find.byKey(const Key('create_invoice_fab'));
  final poDropdown = find.byKey(const Key('invoice_po_dropdown'));
  final invoiceNumberField = find.byKey(const Key('invoice_number_input'));
  final amountField = find.byKey(const Key('invoice_amount_input'));
  final submitButton = find.byKey(const Key('invoice_submit_button'));

  Future<void> verifyInvoiceListLoaded() async {
    await tester.pumpAndSettle(const Duration(seconds: 5));
    // At least one invoice item should be visible
    expect(find.byKey(const Key('invoice_item_inv-001')), findsOneWidget);
  }

  Future<void> tapCreateInvoice() async {
    await tester.tap(createInvoiceButton);
    await tester.pumpAndSettle(const Duration(seconds: 5));
  }

  Future<void> selectPO(String? poNumber) async {
    await tester.tap(poDropdown);
    await tester.pumpAndSettle();
    await tester.tap(find.text(poNumber ?? '').first);
    await tester.pumpAndSettle();
  }

  Future<void> enterInvoiceDetails(String number, String amount) async {
    await tester.enterText(invoiceNumberField, number);
    await tester.enterText(amountField, amount);
    await tester.pump();
  }

  Future<void> submit() async {
    await tester.tap(submitButton);
    await tester.pumpAndSettle(const Duration(seconds: 5));
  }
}
