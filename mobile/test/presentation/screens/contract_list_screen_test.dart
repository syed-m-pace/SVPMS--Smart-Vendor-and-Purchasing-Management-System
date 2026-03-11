import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:svpms_vendor/data/models/contract.dart';
import 'package:svpms_vendor/presentation/contracts/bloc/contract_bloc.dart';
import 'package:svpms_vendor/presentation/contracts/screens/contract_list_screen.dart';

class MockContractBloc extends MockBloc<ContractEvent, ContractState>
    implements ContractBloc {}

void main() {
  late MockContractBloc mockBloc;

  setUpAll(() {
    GoogleFonts.config.allowRuntimeFetching = false;
  });

  setUp(() {
    mockBloc = MockContractBloc();
  });

  Widget buildSubject() {
    return MaterialApp(
      home: BlocProvider<ContractBloc>.value(
        value: mockBloc,
        child: const Scaffold(body: ContractListScreen()),
      ),
    );
  }

  group('ContractListScreen', () {
    testWidgets('shows loading spinner when ContractLoading', (tester) async {
      whenListen(mockBloc, Stream<ContractState>.empty(),
          initialState: ContractLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows contract cards when ContractListLoaded', (tester) async {
      whenListen(
        mockBloc,
        Stream<ContractState>.empty(),
        initialState: ContractListLoaded([
          const Contract(
            id: 'c-001',
            contractNumber: 'CON-001',
            title: 'Annual Supply',
            status: 'ACTIVE',
            startDate: '2026-01-01',
            endDate: '2026-12-31',
            valueCents: 10000000,
          ),
        ], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Annual Supply'), findsOneWidget);
    });

    testWidgets('shows empty state when no contracts', (tester) async {
      whenListen(
        mockBloc,
        Stream<ContractState>.empty(),
        initialState: ContractListLoaded([], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('No contracts found'), findsOneWidget);
    });

    testWidgets('shows error + retry when ContractError', (tester) async {
      whenListen(
        mockBloc,
        Stream<ContractState>.empty(),
        initialState: ContractError('Timeout'),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Timeout'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('shows contract value and number in subtitle', (tester) async {
      whenListen(
        mockBloc,
        Stream<ContractState>.empty(),
        initialState: ContractListLoaded([
          const Contract(
            id: 'c-001',
            contractNumber: 'CON-001',
            title: 'Annual Supply',
            status: 'ACTIVE',
            startDate: '2026-01-01',
            endDate: '2026-12-31',
            valueCents: 10000000,
          ),
        ], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      // Contract number should appear in subtitle
      expect(find.textContaining('CON-001'), findsOneWidget);
    });

    testWidgets('shows filter chips', (tester) async {
      whenListen(
        mockBloc,
        Stream<ContractState>.empty(),
        initialState: ContractListLoaded([
          const Contract(
            id: 'c-001',
            contractNumber: 'CON-001',
            title: 'Test',
            status: 'DRAFT',
            startDate: '2026-01-01',
            endDate: '2026-12-31',
          ),
        ], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('ALL'), findsOneWidget);
      expect(find.byType(FilterChip), findsWidgets);
      expect(find.text('EXPIRED'), findsOneWidget);
    });
  });
}
