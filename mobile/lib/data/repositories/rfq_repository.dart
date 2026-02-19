import 'package:dio/dio.dart';
import '../datasources/api/api_client.dart';
import '../models/rfq.dart';
import '../../services/local_cache_service.dart';

class RFQRepository {
  final ApiClient _api;
  final LocalCacheService _cache;

  RFQRepository({required ApiClient api, required LocalCacheService cache})
    : _api = api,
      _cache = cache;

  Future<List<RFQ>> list({String? status, int page = 1}) async {
    try {
      final data = await _api.getRFQs(status: status, page: page);
      final items = data['items'] as List<dynamic>? ?? [];
      if (page == 1 && status == null) {
        await _cache.cacheRFQs(items);
      }
      return items
          .map((e) => RFQ.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (e) {
      if (e is DioException) {
        final cached = _cache.getCachedRFQs();
        if (cached != null) {
          return cached
              .map((e) => RFQ.fromJson(e as Map<String, dynamic>))
              .toList();
        }
      }
      rethrow;
    }
  }

  Future<RFQ> getById(String id) async {
    try {
      final data = await _api.getRFQ(id);
      return RFQ.fromJson(data);
    } catch (e) {
      if (e is DioException) {
        final cached = _cache.getCachedRFQs();
        if (cached != null) {
          final found = cached.firstWhere(
            (item) => item['id'] == id,
            orElse: () => null,
          );
          if (found != null) {
            return RFQ.fromJson(found as Map<String, dynamic>);
          }
        }
      }
      rethrow;
    }
  }

  Future<void> submitBid(
    String rfqId, {
    required int unitPriceCents,
    required int leadTimeDays,
    String? comments,
  }) async {
    await _api.submitBid(rfqId, {
      'unit_price_cents': unitPriceCents,
      'lead_time_days': leadTimeDays,
      if (comments != null && comments.isNotEmpty) 'comments': comments,
    });
  }
}
