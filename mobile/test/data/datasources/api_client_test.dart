import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/data/datasources/api/api_client.dart';
import '../../helpers/mocks.dart';
import '../../helpers/fixtures.dart';

/// A fake HttpClientAdapter that returns canned responses for specific paths.
class MockHttpClientAdapter extends Mock implements HttpClientAdapter {}

/// Build a [ResponseBody] from JSON data.
ResponseBody _jsonResponse(dynamic data, {int statusCode = 200}) {
  final bytes = utf8.encode(json.encode(data));
  return ResponseBody.fromBytes(
    bytes,
    statusCode,
    headers: {
      'content-type': ['application/json'],
    },
  );
}

void main() {
  late MockStorageService mockStorage;
  late ApiClient client;
  late MockHttpClientAdapter mockAdapter;

  setUpAll(() {
    registerFallbackValue(RequestOptions(path: '/'));
  });

  setUp(() {
    mockStorage = MockStorageService();
    // Stub storage so interceptor doesn't throw
    when(() => mockStorage.accessToken).thenAnswer((_) async => 'test-token');
    when(() => mockStorage.refreshToken).thenAnswer((_) async => null);

    client = ApiClient(storage: mockStorage);
    mockAdapter = MockHttpClientAdapter();
    client.dio.httpClientAdapter = mockAdapter;
  });

  tearDown(() {
    mockAdapter.close();
  });

  void stubRequest(dynamic responseData, {int statusCode = 200}) {
    when(() => mockAdapter.fetch(any(), any(), any())).thenAnswer(
      (_) async => _jsonResponse(responseData, statusCode: statusCode),
    );
  }

  group('login', () {
    test('POST /auth/login and returns data', () async {
      stubRequest({'access_token': 'at', 'refresh_token': 'rt'});

      final result = await client.login('a@b.com', 'pass');
      expect(result['access_token'], 'at');
    });
  });

  group('getDashboard', () {
    test('GET /api/v1/dashboard/stats returns normalized map', () async {
      stubRequest({
        'active_pos': 5,
        'open_invoices': 3,
        'pending_rfqs': 2,
        'pending_prs': 1,
        'budget_utilization': 60,
      });

      final result = await client.getDashboard();
      expect(result['active_pos'], 5);
      expect(result['stats'], isNotNull);
    });

    test('getDashboard returns fallback on error', () async {
      when(() => mockAdapter.fetch(any(), any(), any()))
          .thenThrow(DioException(
        requestOptions: RequestOptions(path: '/dashboard'),
        type: DioExceptionType.connectionError,
      ));

      final result = await client.getDashboard();
      expect(result['active_pos'], 0);
    });
  });

  group('getPurchaseOrders', () {
    test('GET /api/v1/purchase-orders with params', () async {
      stubRequest({
        'data': [makePurchaseOrderJson()],
      });

      final result = await client.getPurchaseOrders(status: 'ISSUED', page: 1);
      expect(result['data'], isA<List>());
    });
  });

  group('getPurchaseOrder', () {
    test('GET /api/v1/purchase-orders/:id', () async {
      stubRequest(makePurchaseOrderJson());

      final result = await client.getPurchaseOrder('po-001');
      expect(result['id'], 'po-001');
    });
  });

  group('acknowledgePO', () {
    test('POST /api/v1/purchase-orders/:id/acknowledge', () async {
      stubRequest(makePurchaseOrderJson(status: 'ACKNOWLEDGED'));

      final result = await client.acknowledgePO('po-001', '2026-03-01');
      expect(result['status'], 'ACKNOWLEDGED');
    });
  });

  group('getRFQs', () {
    test('GET /api/v1/rfqs with params', () async {
      stubRequest({'data': [makeRFQJson()]});

      final result = await client.getRFQs(page: 1);
      expect(result['data'], isA<List>());
    });
  });

  group('getRFQ', () {
    test('GET /api/v1/rfqs/:id', () async {
      stubRequest(makeRFQJson());

      final result = await client.getRFQ('rfq-001');
      expect(result['id'], 'rfq-001');
    });
  });

  group('submitBid', () {
    test('POST /api/v1/rfqs/:rfqId/bids', () async {
      stubRequest({'id': 'bid-001'});

      final result = await client.submitBid('rfq-001', {
        'total_cents': 50000,
        'delivery_days': 7,
      });
      expect(result['id'], 'bid-001');
    });
  });

  group('getInvoices', () {
    test('GET /api/v1/invoices', () async {
      stubRequest({'data': [makeInvoiceJson()]});

      final result = await client.getInvoices(page: 1);
      expect(result['data'], isA<List>());
    });
  });

  group('getInvoice', () {
    test('GET /api/v1/invoices/:id', () async {
      stubRequest(makeInvoiceJson());

      final result = await client.getInvoice('inv-001');
      expect(result['id'], 'inv-001');
    });
  });

  group('createInvoice', () {
    test('POST /api/v1/invoices', () async {
      stubRequest(makeInvoiceJson());

      final result = await client.createInvoice(
        poId: 'po-001',
        invoiceNumber: 'INV-001',
        invoiceDate: '2026-01-20',
        totalCents: 500000,
      );
      expect(result['id'], 'inv-001');
    });
  });

  group('disputeInvoice', () {
    test('POST /api/v1/invoices/:id/dispute', () async {
      stubRequest(makeInvoiceJson(status: 'DISPUTED'));

      final result = await client.disputeInvoice('inv-001', reason: 'Wrong');
      expect(result['status'], 'DISPUTED');
    });
  });

  group('reuploadInvoice', () {
    test('POST /api/v1/invoices/:id/reupload', () async {
      stubRequest(makeInvoiceJson());

      final result = await client.reuploadInvoice('inv-001', 'new-key');
      expect(result['id'], 'inv-001');
    });
  });

  group('getFilePresignedUrl', () {
    test('GET /api/v1/files/:key', () async {
      stubRequest({'presigned_url': 'https://example.com/file'});

      final result = await client.getFilePresignedUrl('key-123');
      expect(result['presigned_url'], 'https://example.com/file');
    });
  });

  group('getNotifications', () {
    test('GET /api/v1/notifications', () async {
      stubRequest({'data': []});

      final result = await client.getNotifications();
      expect(result['data'], isA<List>());
    });
  });

  group('markNotificationRead', () {
    test('POST /api/v1/notifications/:id/read', () async {
      stubRequest({});

      await client.markNotificationRead('n-001');
      // No throw = success
    });
  });

  group('getMe', () {
    test('GET /api/v1/users/me', () async {
      stubRequest(makeUserJson());

      final result = await client.getMe();
      expect(result['email'], 'vendor@test.com');
    });
  });

  group('updateProfile', () {
    test('GET /users/me then PUT /users/:id', () async {
      // First call returns user (for getMe), second returns updated user
      var callCount = 0;
      when(() => mockAdapter.fetch(any(), any(), any())).thenAnswer((_) async {
        callCount++;
        if (callCount == 1) {
          return _jsonResponse(makeUserJson());
        }
        return _jsonResponse(makeUserJson(firstName: 'Updated'));
      });

      final result = await client.updateProfile({'first_name': 'Updated'});
      expect(result['first_name'], 'Updated');
    });
  });

  group('changePassword', () {
    test('POST /api/v1/auth/change-password', () async {
      stubRequest({});

      await client.changePassword('old', 'new');
      // No throw = success
    });
  });

  group('getContracts', () {
    test('GET /api/v1/contracts', () async {
      stubRequest({'data': [makeContractJson()]});

      final result = await client.getContracts(page: 1);
      expect(result['data'], isA<List>());
    });
  });

  group('getContract', () {
    test('GET /api/v1/contracts/:id', () async {
      stubRequest(makeContractJson());

      final result = await client.getContract('c-001');
      expect(result['id'], 'c-001');
    });
  });

  group('setOnAuthFailure', () {
    test('registers callback', () {
      var called = false;
      client.setOnAuthFailure(() => called = true);
      // The callback is stored; we verify it doesn't throw
      expect(called, false);
    });
  });

  group('getRFQs with status filter', () {
    test('GET /api/v1/rfqs?status=OPEN', () async {
      stubRequest({'data': [makeRFQJson()]});

      final result = await client.getRFQs(status: 'OPEN', page: 1);
      expect(result['data'], isA<List>());
    });
  });

  group('getInvoices with status filter', () {
    test('GET /api/v1/invoices?status=UPLOADED', () async {
      stubRequest({'data': [makeInvoiceJson()]});

      final result = await client.getInvoices(status: 'UPLOADED', page: 1);
      expect(result['data'], isA<List>());
    });
  });

  group('createInvoice with documentKey', () {
    test('POST /api/v1/invoices includes document_key', () async {
      stubRequest(makeInvoiceJson());

      final result = await client.createInvoice(
        poId: 'po-001',
        invoiceNumber: 'INV-001',
        invoiceDate: '2026-01-20',
        totalCents: 500000,
        documentKey: 'doc-key-123',
      );
      expect(result['id'], 'inv-001');
    });
  });

  group('getContracts with status filter', () {
    test('GET /api/v1/contracts?status=ACTIVE', () async {
      stubRequest({'data': [makeContractJson()]});

      final result = await client.getContracts(status: 'ACTIVE', page: 1);
      expect(result['data'], isA<List>());
    });
  });

  group('getVendorScorecard', () {
    test('GET /api/v1/vendors/:id/scorecard', () async {
      stubRequest({
        'vendor_id': 'v-001',
        'overall_score': 85,
      });

      final result = await client.getVendorScorecard('v-001');
      expect(result['overall_score'], 85);
    });
  });

  group('updateFCMToken', () {
    test('POST /api/v1/users/me/devices', () async {
      stubRequest({});

      await client.updateFCMToken('fcm-token-123', 'android');
      // No throw = success
    });
  });

  group('getVendorMe', () {
    test('GET /api/v1/vendors/me', () async {
      stubRequest({'id': 'v-001', 'company_name': 'Alpha'});

      final result = await client.getVendorMe();
      expect(result['id'], 'v-001');
    });
  });
}
