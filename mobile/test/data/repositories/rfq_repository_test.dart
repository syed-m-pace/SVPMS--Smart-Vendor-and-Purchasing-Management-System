import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/data/repositories/rfq_repository.dart';
import '../../helpers/mocks.dart';
import '../../helpers/fixtures.dart';

void main() {
  late MockApiClient mockApi;
  late MockLocalCacheService mockCache;
  late RFQRepository repo;

  setUp(() {
    mockApi = MockApiClient();
    mockCache = MockLocalCacheService();
    repo = RFQRepository(api: mockApi, cache: mockCache);
  });

  group('list', () {
    test('returns RFQs and caches first page', () async {
      when(() => mockApi.getRFQs(page: 1)).thenAnswer(
        (_) async => {'data': [makeRFQJson()]},
      );
      when(() => mockCache.cacheRFQs(any())).thenAnswer((_) async {});

      final rfqs = await repo.list();
      expect(rfqs.length, 1);
      expect(rfqs.first.title, 'Office Furniture');
      verify(() => mockCache.cacheRFQs(any())).called(1);
    });

    test('falls back to cache on DioException', () async {
      when(() => mockApi.getRFQs(page: 1)).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/rfqs')),
      );
      when(() => mockCache.getCachedRFQs()).thenReturn([makeRFQJson()]);

      final rfqs = await repo.list();
      expect(rfqs.length, 1);
    });

    test('rethrows when no cache', () async {
      when(() => mockApi.getRFQs(page: 1)).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/rfqs')),
      );
      when(() => mockCache.getCachedRFQs()).thenReturn(null);

      expect(() => repo.list(), throwsA(isA<DioException>()));
    });
  });

  group('getById', () {
    test('returns RFQ from API', () async {
      when(() => mockApi.getRFQ('rfq-001'))
          .thenAnswer((_) async => makeRFQJson());

      final rfq = await repo.getById('rfq-001');
      expect(rfq.id, 'rfq-001');
    });

    test('falls back to cached list', () async {
      when(() => mockApi.getRFQ('rfq-001')).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/rfq')),
      );
      when(() => mockCache.getCachedRFQs()).thenReturn([makeRFQJson()]);

      final rfq = await repo.getById('rfq-001');
      expect(rfq.id, 'rfq-001');
    });
  });

  group('submitBid', () {
    test('sends bid data to API', () async {
      when(() => mockApi.submitBid('rfq-001', any()))
          .thenAnswer((_) async => {});

      await repo.submitBid(
        'rfq-001',
        unitPriceCents: 50000,
        leadTimeDays: 7,
        comments: 'Fast delivery',
      );
      verify(() => mockApi.submitBid('rfq-001', {
            'total_cents': 50000,
            'delivery_days': 7,
            'notes': 'Fast delivery',
          })).called(1);
    });
  });
}
