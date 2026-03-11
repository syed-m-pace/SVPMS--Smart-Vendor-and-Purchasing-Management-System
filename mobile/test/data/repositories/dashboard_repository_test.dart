import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/data/repositories/dashboard_repository.dart';
import '../../helpers/mocks.dart';
import '../../helpers/fixtures.dart';

void main() {
  late MockApiClient mockApi;
  late MockLocalCacheService mockCache;
  late DashboardRepository repo;

  setUp(() {
    mockApi = MockApiClient();
    mockCache = MockLocalCacheService();
    repo = DashboardRepository(api: mockApi, cache: mockCache);
  });

  group('getStats', () {
    test('fetches from API, caches, and returns stats', () async {
      final dashJson = {
        'active_pos': 5,
        'open_invoices': 3,
        'pending_rfqs': 2,
        'pending_prs': 1,
        'budget_utilization': 50,
        'stats': {
          'total_pos': 5,
          'total_invoices': 3,
          'total_rfqs': 2,
          'pending_actions': 1,
        },
      };
      when(() => mockApi.getDashboard()).thenAnswer((_) async => dashJson);
      when(() => mockCache.cacheDashboard(any())).thenAnswer((_) async {});

      final stats = await repo.getStats();
      expect(stats.activePOs, 5);
      expect(stats.openInvoices, 3);
      verify(() => mockCache.cacheDashboard(any())).called(1);
    });

    test('falls back to cache on DioException', () async {
      when(() => mockApi.getDashboard()).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/dashboard')),
      );
      when(() => mockCache.getCachedDashboard()).thenReturn(
        makeDashboardStatsJson(activePOs: 10),
      );

      final stats = await repo.getStats();
      expect(stats.activePOs, 10);
    });

    test('rethrows when no cache available', () async {
      when(() => mockApi.getDashboard()).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/dashboard')),
      );
      when(() => mockCache.getCachedDashboard()).thenReturn(null);

      expect(() => repo.getStats(), throwsA(isA<DioException>()));
    });
  });

  group('getRecentPOs', () {
    test('returns list from data key', () async {
      when(() => mockApi.getPurchaseOrders(page: 1, limit: 5)).thenAnswer(
        (_) async => {
          'data': [makePurchaseOrderJson(), makePurchaseOrderJson(id: 'po-002')],
        },
      );

      final pos = await repo.getRecentPOs();
      expect(pos.length, 2);
    });

    test('returns list from items key', () async {
      when(() => mockApi.getPurchaseOrders(page: 1, limit: 5)).thenAnswer(
        (_) async => {
          'items': [makePurchaseOrderJson()],
        },
      );

      final pos = await repo.getRecentPOs();
      expect(pos.length, 1);
    });

    test('returns empty list on error', () async {
      when(() => mockApi.getPurchaseOrders(page: 1, limit: 5)).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/pos')),
      );
      when(() => mockCache.getCachedPOs()).thenReturn(null);

      final pos = await repo.getRecentPOs();
      expect(pos, isEmpty);
    });
  });
}
