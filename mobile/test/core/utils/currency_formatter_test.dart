import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/core/utils/currency_formatter.dart';

void main() {
  group('formatCurrency', () {
    test('formats 50000 cents as INR', () {
      final result = formatCurrency(50000);
      // Indian number format: ₹500.00
      expect(result, contains('500.00'));
      expect(result, contains('₹'));
    });

    test('formats 0 cents', () {
      final result = formatCurrency(0);
      expect(result, contains('0.00'));
    });

    test('formats 99 cents', () {
      final result = formatCurrency(99);
      expect(result, contains('0.99'));
    });

    test('formats large amount with Indian grouping', () {
      final result = formatCurrency(10000000);
      // 10,000,000 cents = ₹1,00,000.00 (Indian format)
      expect(result, contains('₹'));
      expect(result, contains('00,000.00'));
    });
  });
}
