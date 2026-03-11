import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/data/models/dashboard_stats.dart';
import 'package:svpms_vendor/data/models/purchase_order.dart';
import 'package:svpms_vendor/presentation/dashboard/bloc/dashboard_bloc.dart';
import 'package:svpms_vendor/presentation/dashboard/screens/dashboard_screen.dart';

class MockDashboardBloc extends MockBloc<DashboardEvent, DashboardState>
    implements DashboardBloc {}

void main() {
  late MockDashboardBloc mockBloc;

  setUpAll(() {
    GoogleFonts.config.allowRuntimeFetching = false;
  });

  setUp(() {
    mockBloc = MockDashboardBloc();
  });

  Widget buildSubject() {
    return MaterialApp(
      home: BlocProvider<DashboardBloc>.value(
        value: mockBloc,
        child: const Scaffold(body: DashboardScreen()),
      ),
    );
  }

  group('DashboardScreen', () {
    testWidgets('shows loading spinner when DashboardLoading', (tester) async {
      whenListen(
        mockBloc,
        Stream<DashboardState>.empty(),
        initialState: DashboardLoading(),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows stat cards when DashboardLoaded', (tester) async {
      final loadedState = DashboardLoaded(
        stats: const DashboardStats(activePOs: 5, pendingRFQs: 2, openInvoices: 3),
        recentPOs: const [],
      );

      whenListen(
        mockBloc,
        Stream<DashboardState>.empty(),
        initialState: loadedState,
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('dashboard_stat_active_pos')), findsOneWidget);
      expect(find.byKey(const Key('dashboard_stat_pending_rfqs')), findsOneWidget);
      expect(find.byKey(const Key('dashboard_stat_open_invoices')), findsOneWidget);
    });

    testWidgets('shows error + retry when DashboardError', (tester) async {
      whenListen(
        mockBloc,
        Stream<DashboardState>.empty(),
        initialState: DashboardError('Network error'),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Network error'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('shows "No purchase orders yet" when recentPOs is empty', (tester) async {
      // Increase viewport height so ListView renders items below the GridView
      tester.view.physicalSize = const Size(800, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      whenListen(
        mockBloc,
        Stream<DashboardState>.empty(),
        initialState: DashboardLoaded(
          stats: const DashboardStats(activePOs: 0, pendingRFQs: 0, openInvoices: 0),
          recentPOs: const [],
        ),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('No purchase orders yet'), findsOneWidget);
    });

    testWidgets('shows PO cards when recentPOs are present', (tester) async {
      tester.view.physicalSize = const Size(800, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      whenListen(
        mockBloc,
        Stream<DashboardState>.empty(),
        initialState: DashboardLoaded(
          stats: const DashboardStats(activePOs: 1, pendingRFQs: 0, openInvoices: 0),
          recentPOs: [
            const PurchaseOrder(
              id: 'po-001',
              poNumber: 'PO-2026-001',
              status: 'ISSUED',
              totalCents: 500000,
            ),
          ],
        ),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('PO-2026-001'), findsOneWidget);
      expect(find.text('Recent Purchase Orders'), findsOneWidget);
    });
  });
}
