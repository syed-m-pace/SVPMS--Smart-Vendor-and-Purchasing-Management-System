import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:svpms_vendor/data/models/purchase_order.dart';
import 'package:svpms_vendor/presentation/purchase_orders/bloc/po_bloc.dart';
import 'package:svpms_vendor/presentation/purchase_orders/screens/po_list_screen.dart';

class MockPOBloc extends MockBloc<POEvent, POState> implements POBloc {}

void main() {
  late MockPOBloc mockBloc;

  setUpAll(() {
    GoogleFonts.config.allowRuntimeFetching = false;
  });

  setUp(() {
    mockBloc = MockPOBloc();
  });

  Widget buildSubject() {
    return MaterialApp(
      home: BlocProvider<POBloc>.value(
        value: mockBloc,
        child: const Scaffold(body: POListScreen()),
      ),
    );
  }

  group('POListScreen', () {
    testWidgets('shows loading spinner when POLoading', (tester) async {
      whenListen(mockBloc, Stream<POState>.empty(), initialState: POLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows PO cards when POListLoaded', (tester) async {
      whenListen(
        mockBloc,
        Stream<POState>.empty(),
        initialState: POListLoaded([
          const PurchaseOrder(
            id: 'po-001',
            poNumber: 'PO-2026-001',
            status: 'ISSUED',
            totalCents: 500000,
            vendorName: 'Alpha',
          ),
        ], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('PO-2026-001'), findsOneWidget);
    });

    testWidgets('shows empty state when no POs', (tester) async {
      whenListen(
        mockBloc,
        Stream<POState>.empty(),
        initialState: POListLoaded([], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('No purchase orders'), findsOneWidget);
    });

    testWidgets('shows error + retry when POError', (tester) async {
      whenListen(
        mockBloc,
        Stream<POState>.empty(),
        initialState: POError('Failed to load'),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Failed to load'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });
  });
}
