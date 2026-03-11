import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:svpms_vendor/data/models/invoice.dart';
import 'package:svpms_vendor/presentation/invoices/bloc/invoice_bloc.dart';
import 'package:svpms_vendor/presentation/invoices/screens/invoice_list_screen.dart';

class MockInvoiceBloc extends MockBloc<InvoiceEvent, InvoiceState>
    implements InvoiceBloc {}

void main() {
  late MockInvoiceBloc mockBloc;

  setUpAll(() {
    GoogleFonts.config.allowRuntimeFetching = false;
  });

  setUp(() {
    mockBloc = MockInvoiceBloc();
  });

  Widget buildSubject() {
    return MaterialApp(
      home: BlocProvider<InvoiceBloc>.value(
        value: mockBloc,
        child: const Scaffold(body: InvoiceListScreen()),
      ),
    );
  }

  group('InvoiceListScreen', () {
    testWidgets('shows loading spinner when InvoiceLoading', (tester) async {
      whenListen(mockBloc, Stream<InvoiceState>.empty(),
          initialState: InvoiceLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows invoice cards when InvoiceListLoaded', (tester) async {
      whenListen(
        mockBloc,
        Stream<InvoiceState>.empty(),
        initialState: InvoiceListLoaded([
          const Invoice(
            id: 'inv-001',
            invoiceNumber: 'INV-001',
            status: 'UPLOADED',
            totalCents: 250000,
            poNumber: 'PO-001',
          ),
        ], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('INV-001'), findsOneWidget);
    });

    testWidgets('shows empty state when no invoices', (tester) async {
      whenListen(
        mockBloc,
        Stream<InvoiceState>.empty(),
        initialState: InvoiceListLoaded([], hasMore: false),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('No invoices'), findsOneWidget);
    });

    testWidgets('shows error + retry when InvoiceError', (tester) async {
      whenListen(
        mockBloc,
        Stream<InvoiceState>.empty(),
        initialState: InvoiceError('Connection failed'),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Connection failed'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });
  });
}
