import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:svpms_vendor/data/models/rfq.dart';
import 'package:svpms_vendor/presentation/rfqs/bloc/rfq_bloc.dart';
import 'package:svpms_vendor/presentation/rfqs/screens/rfq_list_screen.dart';

class MockRFQBloc extends MockBloc<RFQEvent, RFQState> implements RFQBloc {}

void main() {
  late MockRFQBloc mockBloc;

  setUpAll(() {
    GoogleFonts.config.allowRuntimeFetching = false;
  });

  setUp(() {
    mockBloc = MockRFQBloc();
  });

  Widget buildSubject() {
    return MaterialApp(
      home: BlocProvider<RFQBloc>.value(
        value: mockBloc,
        child: const Scaffold(body: RFQListScreen()),
      ),
    );
  }

  group('RFQListScreen', () {
    testWidgets('shows loading spinner when RFQLoading', (tester) async {
      whenListen(mockBloc, Stream<RFQState>.empty(),
          initialState: RFQLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows RFQ cards when RFQListLoaded', (tester) async {
      whenListen(
        mockBloc,
        Stream<RFQState>.empty(),
        initialState: RFQListLoaded([
          const RFQ(
            id: 'rfq-001',
            rfqNumber: 'RFQ-001',
            title: 'Office Furniture',
            status: 'OPEN',
          ),
        ], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Office Furniture'), findsOneWidget);
    });

    testWidgets('shows empty state when no RFQs', (tester) async {
      whenListen(
        mockBloc,
        Stream<RFQState>.empty(),
        initialState: RFQListLoaded([], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('No RFQs available'), findsOneWidget);
    });

    testWidgets('shows error + retry when RFQError', (tester) async {
      whenListen(
        mockBloc,
        Stream<RFQState>.empty(),
        initialState: RFQError('Server error'),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Server error'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('shows "Bid Submitted" badge when RFQ has bids', (tester) async {
      whenListen(
        mockBloc,
        Stream<RFQState>.empty(),
        initialState: RFQListLoaded([
          const RFQ(
            id: 'rfq-001',
            rfqNumber: 'RFQ-001',
            title: 'Supplies',
            status: 'OPEN',
            bids: [
              RFQBid(id: 'b-1', vendorId: 'v-001', totalCents: 5000, deliveryDays: 7),
            ],
          ),
        ], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Bid Submitted'), findsOneWidget);
    });

    testWidgets('shows deadline text when RFQ has deadline', (tester) async {
      whenListen(
        mockBloc,
        Stream<RFQState>.empty(),
        initialState: RFQListLoaded([
          const RFQ(
            id: 'rfq-002',
            rfqNumber: 'RFQ-002',
            title: 'Hardware',
            status: 'OPEN',
            deadline: '2026-02-28T23:59:59Z',
          ),
        ], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.textContaining('Deadline:'), findsOneWidget);
    });

    testWidgets('shows won badge for awarded RFQ matching vendor', (tester) async {
      whenListen(
        mockBloc,
        Stream<RFQState>.empty(),
        initialState: RFQListLoaded([
          const RFQ(
            id: 'rfq-003',
            rfqNumber: 'RFQ-003',
            title: 'Won RFQ',
            status: 'AWARDED',
            awardedVendorId: 'v-001',
            bids: [
              RFQBid(id: 'b-1', vendorId: 'v-001', totalCents: 5000, deliveryDays: 7),
            ],
          ),
        ], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.textContaining('You Won'), findsOneWidget);
    });

    testWidgets('shows lost badge for awarded RFQ not matching vendor', (tester) async {
      whenListen(
        mockBloc,
        Stream<RFQState>.empty(),
        initialState: RFQListLoaded([
          const RFQ(
            id: 'rfq-004',
            rfqNumber: 'RFQ-004',
            title: 'Lost RFQ',
            status: 'AWARDED',
            awardedVendorId: 'v-999',
            bids: [
              RFQBid(id: 'b-1', vendorId: 'v-001', totalCents: 5000, deliveryDays: 7),
            ],
          ),
        ], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Awarded to another vendor'), findsOneWidget);
    });
  });
}
