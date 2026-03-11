import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/data/repositories/po_repository.dart';
import '../../helpers/mocks.dart';
import '../../helpers/fixtures.dart';

void main() {
  late MockApiClient mockApi;
  late MockLocalCacheService mockCache;
  late PORepository repo;

  setUp(() {
    mockApi = MockApiClient();
    mockCache = MockLocalCacheService();
    repo = PORepository(api: mockApi, cache: mockCache);
  });

  group('list', () {
    test('returns POs and caches first page', () async {
      when(() => mockApi.getPurchaseOrders(page: 1)).thenAnswer(
        (_) async => {
          'data': [makePurchaseOrderJson()],
        },
      );
      when(() => mockCache.cachePOs(any())).thenAnswer((_) async {});

      final pos = await repo.list();
      expect(pos.length, 1);
      expect(pos.first.poNumber, 'PO-2026-001');
      verify(() => mockCache.cachePOs(any())).called(1);
    });

    test('passes status filter and does not cache', () async {
      when(() => mockApi.getPurchaseOrders(status: 'ISSUED', page: 1))
          .thenAnswer((_) async => {'data': [makePurchaseOrderJson()]});

      final pos = await repo.list(status: 'ISSUED');
      expect(pos.length, 1);
      verifyNever(() => mockCache.cachePOs(any()));
    });

    test('falls back to cache on DioException', () async {
      when(() => mockApi.getPurchaseOrders(page: 1)).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/pos')),
      );
      when(() => mockCache.getCachedPOs()).thenReturn([makePurchaseOrderJson()]);

      final pos = await repo.list();
      expect(pos.length, 1);
    });

    test('rethrows when no cache', () async {
      when(() => mockApi.getPurchaseOrders(page: 1)).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/pos')),
      );
      when(() => mockCache.getCachedPOs()).thenReturn(null);

      expect(() => repo.list(), throwsA(isA<DioException>()));
    });
  });

  group('getById', () {
    test('returns PO from API', () async {
      when(() => mockApi.getPurchaseOrder('po-001'))
          .thenAnswer((_) async => makePurchaseOrderJson());

      final po = await repo.getById('po-001');
      expect(po.id, 'po-001');
    });

    test('falls back to cached list', () async {
      when(() => mockApi.getPurchaseOrder('po-001')).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/po')),
      );
      when(() => mockCache.getCachedPOs()).thenReturn([makePurchaseOrderJson()]);

      final po = await repo.getById('po-001');
      expect(po.id, 'po-001');
    });
  });

  group('acknowledge', () {
    test('sends delivery date and returns updated PO', () async {
      when(() => mockApi.acknowledgePO('po-001', '2026-03-01')).thenAnswer(
        (_) async => makePurchaseOrderJson(status: 'ACKNOWLEDGED'),
      );

      final po = await repo.acknowledge('po-001', '2026-03-01');
      expect(po.status, 'ACKNOWLEDGED');
    });
  });
}
