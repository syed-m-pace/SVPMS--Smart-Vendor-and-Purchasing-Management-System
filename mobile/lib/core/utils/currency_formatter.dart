import 'package:intl/intl.dart';

/// Format cents to INR currency string
String formatCurrency(int cents) {
  return NumberFormat.currency(
    locale: 'en_IN',
    symbol: '₹',
    decimalDigits: 2,
  ).format(cents / 100);
}
