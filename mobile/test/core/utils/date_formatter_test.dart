import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/core/utils/date_formatter.dart';

void main() {
  group('formatDate', () {
    test('formats ISO string to dd MMM yyyy', () {
      expect(formatDate('2026-03-05T10:00:00Z'), '05 Mar 2026');
    });

    test('returns N/A for null', () {
      expect(formatDate(null), 'N/A');
    });

    test('returns raw string for invalid date', () {
      expect(formatDate('not-a-date'), 'not-a-date');
    });

    test('formats date-only string', () {
      expect(formatDate('2026-01-15'), '15 Jan 2026');
    });
  });

  group('timeAgo', () {
    test('returns "just now" for less than a minute', () {
      final now = DateTime.now().subtract(const Duration(seconds: 30));
      expect(timeAgo(now.toIso8601String()), 'just now');
    });

    test('returns minutes ago', () {
      final past = DateTime.now().subtract(const Duration(minutes: 5));
      expect(timeAgo(past.toIso8601String()), '5m ago');
    });

    test('returns hours ago', () {
      final past = DateTime.now().subtract(const Duration(hours: 3));
      expect(timeAgo(past.toIso8601String()), '3h ago');
    });

    test('returns days ago', () {
      final past = DateTime.now().subtract(const Duration(days: 2));
      expect(timeAgo(past.toIso8601String()), '2d ago');
    });

    test('returns formatted date for > 7 days', () {
      final past = DateTime.now().subtract(const Duration(days: 10));
      final result = timeAgo(past.toIso8601String());
      // Should return formatted date, not "Xd ago"
      expect(result, isNot(contains('d ago')));
    });
  });
}
