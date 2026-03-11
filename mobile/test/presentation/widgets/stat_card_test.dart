import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/presentation/widgets/stat_card.dart';

void main() {
  group('StatCard', () {
    testWidgets('renders title, value, and icon', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: StatCard(
              title: 'Active POs',
              value: '5',
              icon: Icons.shopping_cart,
            ),
          ),
        ),
      );

      expect(find.text('Active POs'), findsOneWidget);
      expect(find.text('5'), findsOneWidget);
      expect(find.byIcon(Icons.shopping_cart), findsOneWidget);
    });

    testWidgets('onTap callback fires', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: StatCard(
              title: 'Test',
              value: '10',
              icon: Icons.info,
              onTap: () => tapped = true,
            ),
          ),
        ),
      );

      await tester.tap(find.text('10'));
      expect(tapped, true);
    });
  });
}
