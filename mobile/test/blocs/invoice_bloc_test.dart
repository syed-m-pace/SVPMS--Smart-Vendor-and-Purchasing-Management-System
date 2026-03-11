import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/presentation/invoices/bloc/invoice_bloc.dart';

import '../helpers/mocks.dart';
import '../helpers/fixtures.dart';

void main() {
  late MockInvoiceRepository mockRepo;

  setUp(() {
    mockRepo = MockInvoiceRepository();
  });

  group('InvoiceBloc', () {
    blocTest<InvoiceBloc, InvoiceState>(
      'emits [InvoiceLoading, InvoiceListLoaded] on LoadInvoices',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: any(named: 'page')))
            .thenAnswer((_) async => [makeInvoice()]);
        return InvoiceBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadInvoices()),
      expect: () => [
        isA<InvoiceLoading>(),
        isA<InvoiceListLoaded>()
            .having((s) => s.invoices.length, 'count', 1)
            .having((s) => s.hasMore, 'hasMore', false),
      ],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'emits [InvoiceLoading, InvoiceListLoaded] with status filter',
      build: () {
        when(() => mockRepo.list(status: 'EXCEPTION', page: 1))
            .thenAnswer((_) async => [makeInvoice(status: 'EXCEPTION')]);
        return InvoiceBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadInvoices(status: 'EXCEPTION')),
      expect: () => [
        isA<InvoiceLoading>(),
        isA<InvoiceListLoaded>()
            .having((s) => s.invoices.first.status, 'status', 'EXCEPTION'),
      ],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'LoadMoreInvoices appends and increments page',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 2))
            .thenAnswer((_) async => [makeInvoice(id: 'inv-new')]);
        return InvoiceBloc(repo: mockRepo);
      },
      seed: () => InvoiceListLoaded(
        [makeInvoice()],
        hasMore: true,
        page: 1,
      ),
      act: (bloc) => bloc.add(LoadMoreInvoices()),
      expect: () => [
        isA<InvoiceListLoaded>().having((s) => s.isLoadingMore, 'loading', true),
        isA<InvoiceListLoaded>()
            .having((s) => s.invoices.length, 'count', 2)
            .having((s) => s.page, 'page', 2),
      ],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'emits [InvoiceLoading, InvoiceUploaded] on successful upload',
      build: () {
        final inv = makeInvoice(status: 'UPLOADED');
        when(() => mockRepo.upload(
              poId: any(named: 'poId'),
              invoiceNumber: any(named: 'invoiceNumber'),
              invoiceDate: any(named: 'invoiceDate'),
              totalCents: any(named: 'totalCents'),
              filePath: any(named: 'filePath'),
            )).thenAnswer((_) async => inv);
        return InvoiceBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(UploadInvoice(
        poId: 'po-001',
        invoiceNumber: 'INV-001',
        invoiceDate: '2026-03-01',
        totalCents: 500000,
      )),
      expect: () => [
        isA<InvoiceLoading>(),
        isA<InvoiceUploaded>(),
      ],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'emits [InvoiceLoading, InvoiceError] when upload fails',
      build: () {
        when(() => mockRepo.upload(
              poId: any(named: 'poId'),
              invoiceNumber: any(named: 'invoiceNumber'),
              invoiceDate: any(named: 'invoiceDate'),
              totalCents: any(named: 'totalCents'),
              filePath: any(named: 'filePath'),
            )).thenThrow(Exception('Upload failed'));
        return InvoiceBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(UploadInvoice(
        poId: 'po-001',
        invoiceNumber: 'INV-001',
        invoiceDate: '2026-03-01',
        totalCents: 500000,
      )),
      expect: () => [
        isA<InvoiceLoading>(),
        isA<InvoiceError>(),
      ],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'emits [InvoiceLoading, InvoiceDisputed] on successful dispute',
      build: () {
        final inv = makeInvoice(status: 'DISPUTED');
        when(() => mockRepo.disputeInvoice(any(), reason: any(named: 'reason')))
            .thenAnswer((_) async => inv);
        return InvoiceBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(DisputeInvoice(
        invoiceId: 'inv-001',
        reason: 'Amount mismatch',
      )),
      expect: () => [
        isA<InvoiceLoading>(),
        isA<InvoiceDisputed>()
            .having((s) => s.invoice.status, 'status', 'DISPUTED'),
      ],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'emits [InvoiceLoading, InvoiceReuploaded] on successful reupload',
      build: () {
        final inv = makeInvoice(status: 'UPLOADED');
        when(() => mockRepo.reuploadInvoice(any(), any()))
            .thenAnswer((_) async => inv);
        return InvoiceBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(ReuploadInvoice(
        invoiceId: 'inv-001',
        filePath: '/tmp/invoice.pdf',
      )),
      expect: () => [
        isA<InvoiceLoading>(),
        isA<InvoiceReuploaded>(),
      ],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'emits [InvoiceLoading, InvoiceError] when LoadInvoices fails',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: any(named: 'page')))
            .thenThrow(Exception('Network error'));
        return InvoiceBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadInvoices()),
      expect: () => [
        isA<InvoiceLoading>(),
        isA<InvoiceError>(),
      ],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'RefreshInvoices emits InvoiceListLoaded',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 1))
            .thenAnswer((_) async => [makeInvoice()]);
        return InvoiceBloc(repo: mockRepo);
      },
      seed: () => InvoiceListLoaded([makeInvoice()], hasMore: false, page: 1),
      act: (bloc) => bloc.add(RefreshInvoices()),
      expect: () => [isA<InvoiceListLoaded>()],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'RefreshInvoices emits InvoiceError on failure',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 1))
            .thenThrow(Exception('Timeout'));
        return InvoiceBloc(repo: mockRepo);
      },
      seed: () => InvoiceListLoaded([makeInvoice()], hasMore: false, page: 1),
      act: (bloc) => bloc.add(RefreshInvoices()),
      expect: () => [isA<InvoiceError>()],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'LoadMoreInvoices does nothing when hasMore is false',
      build: () => InvoiceBloc(repo: mockRepo),
      seed: () => InvoiceListLoaded([makeInvoice()], hasMore: false, page: 1),
      act: (bloc) => bloc.add(LoadMoreInvoices()),
      expect: () => [],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'LoadMoreInvoices recovers on error',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 2))
            .thenThrow(Exception('Network error'));
        return InvoiceBloc(repo: mockRepo);
      },
      seed: () => InvoiceListLoaded([makeInvoice()], hasMore: true, page: 1),
      act: (bloc) => bloc.add(LoadMoreInvoices()),
      expect: () => [
        isA<InvoiceListLoaded>().having((s) => s.isLoadingMore, 'loading', true),
        isA<InvoiceListLoaded>()
            .having((s) => s.invoices.length, 'count', 1)
            .having((s) => s.page, 'page', 1),
      ],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'DisputeInvoice emits InvoiceError on failure',
      build: () {
        when(() => mockRepo.disputeInvoice(any(), reason: any(named: 'reason')))
            .thenThrow(Exception('Server error'));
        return InvoiceBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(DisputeInvoice(invoiceId: 'inv-001', reason: 'Bad')),
      expect: () => [
        isA<InvoiceLoading>(),
        isA<InvoiceError>(),
      ],
    );

    blocTest<InvoiceBloc, InvoiceState>(
      'ReuploadInvoice emits InvoiceError on failure',
      build: () {
        when(() => mockRepo.reuploadInvoice(any(), any()))
            .thenThrow(Exception('Upload failed'));
        return InvoiceBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(ReuploadInvoice(invoiceId: 'inv-001', filePath: '/tmp/f.pdf')),
      expect: () => [
        isA<InvoiceLoading>(),
        isA<InvoiceError>(),
      ],
    );
  });
}
