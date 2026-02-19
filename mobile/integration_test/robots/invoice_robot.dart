import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class InvoiceRobot {
  final WidgetTester tester;

  InvoiceRobot(this.tester);

  // Finders
  final createInvoiceButton = find.byKey(const Key('create_invoice_fab'));
  final poDropdown = find.byKey(const Key('invoice_po_dropdown'));
  final invoiceNumberField = find.byKey(const Key('invoice_number_input'));
  final amountField = find.byKey(const Key('invoice_amount_input'));
  final uploadButton = find.byKey(const Key('invoice_upload_file_button'));
  final submitButton = find.byKey(const Key('invoice_submit_button'));

  Future<void> tapCreateInvoice() async {
    await tester.tap(createInvoiceButton);
    await tester.pumpAndSettle();
  }

  Future<void> selectPO(String? poNumber) async {
    // Handling dropdowns in integration tests can be tricky;
    // assuming first available is sufficient for flow test or specific widget key
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
    await tester.pumpAndSettle();
  }
}
