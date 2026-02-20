import 'package:dio/dio.dart';
import '../datasources/api/api_client.dart';
import '../models/purchase_order.dart';
import '../../services/local_cache_service.dart';

class PORepository {
  final ApiClient _api;
  final LocalCacheService _cache;

  PORepository({required ApiClient api, required LocalCacheService cache})
    : _api = api,
      _cache = cache;

  Future<List<PurchaseOrder>> list({String? status, int page = 1}) async {
    try {
      final data = await _api.getPurchaseOrders(status: status, page: page);
      final items =
          data['data'] as List<dynamic>? ??
          data['items'] as List<dynamic>? ??
          [];
      // Cache the list if it's the first page
      if (page == 1 && status == null) {
        await _cache.cachePOs(items);
      }
      return items
          .map((e) => PurchaseOrder.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (e) {
      if (e is DioException) {
        final cached = _cache.getCachedPOs();
        if (cached != null) {
          return cached
              .map((e) => PurchaseOrder.fromJson(e as Map<String, dynamic>))
              .toList();
        }
      }
      rethrow;
    }
  }

  Future<PurchaseOrder> getById(String id) async {
    try {
      final data = await _api.getPurchaseOrder(id);
      // Could cache individually, but for now rely on list cache + fresh fetch
      return PurchaseOrder.fromJson(data);
    } catch (e) {
      if (e is DioException) {
        // Try to find in list cache
        final cached = _cache.getCachedPOs();
        if (cached != null) {
          final found = cached.firstWhere(
            (e) => e['id'] == id,
            orElse: () => null,
          );
          if (found != null) {
            return PurchaseOrder.fromJson(found);
          }
        }
      }
      rethrow;
    }
  }

  Future<PurchaseOrder> acknowledge(
    String id,
    String expectedDeliveryDate,
  ) async {
    final data = await _api.acknowledgePO(id, expectedDeliveryDate);
    return PurchaseOrder.fromJson(data);
  }
}
