import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/data/repositories/invoice_repository.dart';
import '../../helpers/mocks.dart';
import '../../helpers/fixtures.dart';

void main() {
  late MockApiClient mockApi;
  late InvoiceRepository repo;

  setUp(() {
    mockApi = MockApiClient();
    repo = InvoiceRepository(api: mockApi);
  });

  group('list', () {
    test('returns invoices from data key', () async {
      when(() => mockApi.getInvoices(page: 1)).thenAnswer(
        (_) async => {'data': [makeInvoiceJson()]},
      );

      final invoices = await repo.list();
      expect(invoices.length, 1);
      expect(invoices.first.invoiceNumber, 'INV-2026-001');
    });

    test('passes status filter', () async {
      when(() => mockApi.getInvoices(status: 'MATCHED', page: 1)).thenAnswer(
        (_) async => {'data': [makeInvoiceJson(status: 'MATCHED')]},
      );

      final invoices = await repo.list(status: 'MATCHED');
      expect(invoices.first.status, 'MATCHED');
    });
  });

  group('get', () {
    test('returns single invoice', () async {
      when(() => mockApi.getInvoice('inv-001'))
          .thenAnswer((_) async => makeInvoiceJson());

      final inv = await repo.get('inv-001');
      expect(inv.id, 'inv-001');
    });
  });

  group('upload', () {
    test('creates invoice without file', () async {
      when(() => mockApi.createInvoice(
            poId: 'po-001',
            invoiceNumber: 'INV-001',
            invoiceDate: '2026-01-20',
            totalCents: 500000,
            documentKey: null,
          )).thenAnswer((_) async => makeInvoiceJson());

      final inv = await repo.upload(
        poId: 'po-001',
        invoiceNumber: 'INV-001',
        invoiceDate: '2026-01-20',
        totalCents: 500000,
      );
      expect(inv.id, 'inv-001');
      verifyNever(() => mockApi.uploadFile(any()));
    });

    test('uploads file first then creates invoice', () async {
      when(() => mockApi.uploadFile('/path/to/file.pdf'))
          .thenAnswer((_) async => {'file_key': 'key-123'});
      when(() => mockApi.createInvoice(
            poId: 'po-001',
            invoiceNumber: 'INV-001',
            invoiceDate: '2026-01-20',
            totalCents: 500000,
            documentKey: 'key-123',
          )).thenAnswer((_) async => makeInvoiceJson());

      final inv = await repo.upload(
        poId: 'po-001',
        invoiceNumber: 'INV-001',
        invoiceDate: '2026-01-20',
        totalCents: 500000,
        filePath: '/path/to/file.pdf',
      );
      expect(inv.id, 'inv-001');
      verify(() => mockApi.uploadFile('/path/to/file.pdf')).called(1);
    });
  });

  group('disputeInvoice', () {
    test('calls dispute endpoint', () async {
      when(() => mockApi.disputeInvoice('inv-001', reason: 'Wrong amount'))
          .thenAnswer((_) async => makeInvoiceJson(status: 'DISPUTED'));

      final inv = await repo.disputeInvoice('inv-001', reason: 'Wrong amount');
      expect(inv.status, 'DISPUTED');
    });
  });

  group('reuploadInvoice', () {
    test('uploads file then calls reupload', () async {
      when(() => mockApi.uploadFile('/new/file.pdf'))
          .thenAnswer((_) async => {'file_key': 'new-key'});
      when(() => mockApi.reuploadInvoice('inv-001', 'new-key'))
          .thenAnswer((_) async => makeInvoiceJson());

      final inv = await repo.reuploadInvoice('inv-001', '/new/file.pdf');
      expect(inv.id, 'inv-001');
    });
  });

  group('getPresignedUrl', () {
    test('returns URL string', () async {
      when(() => mockApi.getFilePresignedUrl('key-123'))
          .thenAnswer((_) async => {'presigned_url': 'https://example.com/file'});

      final url = await repo.getPresignedUrl('key-123');
      expect(url, 'https://example.com/file');
    });
  });
}
