import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/presentation/widgets/status_badge.dart';
import 'package:svpms_vendor/core/constants/app_colors.dart';

void main() {
  group('StatusBadge', () {
    testWidgets('renders status text with underscores replaced', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: StatusBadge(status: 'PENDING_APPROVAL'))),
      );

      expect(find.text('PENDING APPROVAL'), findsOneWidget);
    });

    testWidgets('applies correct color for APPROVED status', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: StatusBadge(status: 'APPROVED'))),
      );

      final text = tester.widget<Text>(find.text('APPROVED'));
      expect(text.style?.color, AppColors.success);
    });

    testWidgets('applies correct color for REJECTED status', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: StatusBadge(status: 'REJECTED'))),
      );

      final text = tester.widget<Text>(find.text('REJECTED'));
      expect(text.style?.color, AppColors.destructive);
    });

    testWidgets('applies correct color for ISSUED status', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: StatusBadge(status: 'ISSUED'))),
      );

      final text = tester.widget<Text>(find.text('ISSUED'));
      expect(text.style?.color, AppColors.accent);
    });
  });
}
