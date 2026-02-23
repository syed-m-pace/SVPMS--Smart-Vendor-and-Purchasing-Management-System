import 'package:dio/dio.dart';
import '../datasources/api/api_client.dart';
import '../models/dashboard_stats.dart';
import '../models/purchase_order.dart';
import '../../services/local_cache_service.dart';

class DashboardRepository {
  final ApiClient _api;
  final LocalCacheService _cache;

  DashboardRepository({
    required ApiClient api,
    required LocalCacheService cache,
  }) : _api = api,
       _cache = cache;

  Future<DashboardStats> getStats() async {
    try {
      final data = await _api.getDashboard();
      await _cache.cacheDashboard(data);
      return DashboardStats.fromJson(data);
    } catch (e) {
      if (e is DioException) {
        final cached = _cache.getCachedDashboard();
        if (cached != null) return DashboardStats.fromJson(cached);
      }
      rethrow;
    }
  }

  Future<List<PurchaseOrder>> getRecentPOs() async {
    try {
      final data = await _api.getPurchaseOrders(page: 1, limit: 5);
      final items =
          data['data'] as List<dynamic>? ??
          data['items'] as List<dynamic>? ??
          [];
      return items
          .map((e) => PurchaseOrder.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (e) {
      if (e is DioException) {
        final cached = _cache.getCachedPOs();
        if (cached != null) {
          return cached
              .take(5)
              .map((e) => PurchaseOrder.fromJson(e as Map<String, dynamic>))
              .toList();
        }
      }
      return [];
    }
  }
}
