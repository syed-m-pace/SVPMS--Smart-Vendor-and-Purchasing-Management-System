import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';
import '../../../services/storage_service.dart';

class ApiClient {
  late final Dio dio;
  final StorageService _storage;

  ApiClient({required StorageService storage}) : _storage = storage {
    dio = Dio(
      BaseOptions(
        baseUrl: ApiConstants.baseUrl,
        connectTimeout: ApiConstants.connectTimeout,
        receiveTimeout: ApiConstants.receiveTimeout,
        headers: {'Content-Type': 'application/json'},
      ),
    );

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.accessToken;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401) {
            final refreshed = await _tryRefresh();
            if (refreshed) {
              final opts = error.requestOptions;
              final token = await _storage.accessToken;
              opts.headers['Authorization'] = 'Bearer $token';
              try {
                final resp = await dio.fetch(opts);
                return handler.resolve(resp);
              } catch (e) {
                return handler.next(error);
              }
            }
          }
          return handler.next(error);
        },
      ),
    );
  }

  Future<bool> _tryRefresh() async {
    final rt = await _storage.refreshToken;
    if (rt == null) return false;
    try {
      final resp = await Dio(
        BaseOptions(baseUrl: ApiConstants.baseUrl),
      ).post('/auth/refresh', data: {'refresh_token': rt});
      await _storage.saveTokens(
        accessToken: resp.data['access_token'],
        refreshToken: resp.data['refresh_token'],
      );
      return true;
    } catch (_) {
      await _storage.clearTokens();
      return false;
    }
  }

  // ─── Auth (root path, no /api/v1 prefix) ──────────────
  Future<Map<String, dynamic>> login(String email, String password) async {
    final resp = await dio.post(
      '/auth/login',
      data: {'email': email, 'password': password},
    );
    return resp.data;
  }

  // ─── Dashboard (aggregated from POs + Invoices) ───────
  /// No dedicated dashboard endpoint exists — we aggregate from other APIs
  Future<Map<String, dynamic>> getDashboard() async {
    try {
      final results = await Future.wait([
        dio.get(
          '/api/v1/purchase-orders',
          queryParameters: {'page': 1, 'limit': 5},
        ),
        dio.get('/api/v1/invoices', queryParameters: {'page': 1, 'limit': 5}),
        dio.get('/api/v1/rfqs', queryParameters: {'page': 1, 'limit': 5}),
      ]);

      final poData = results[0].data;
      final invoiceData = results[1].data;
      final rfqData = results[2].data;

      final poItems = poData['data'] ?? poData['items'] ?? [];
      final invoiceItems = invoiceData['data'] ?? invoiceData['items'] ?? [];
      final rfqItems = rfqData['data'] ?? rfqData['items'] ?? [];

      final poTotal =
          poData['pagination']?['total'] ??
          poData['total'] ??
          (poItems as List?)?.length ??
          0;
      final invoiceTotal =
          invoiceData['pagination']?['total'] ??
          invoiceData['total'] ??
          (invoiceItems as List?)?.length ??
          0;
      final rfqTotal =
          rfqData['pagination']?['total'] ??
          rfqData['total'] ??
          (rfqItems as List?)?.length ??
          0;

      return {
        'active_pos': poTotal,
        'open_invoices': invoiceTotal,
        'pending_rfqs': rfqTotal,
        'pending_prs': 0,
        'stats': {
          // Kept for backwards compatibility if needed
          'total_pos': poTotal,
          'total_invoices': invoiceTotal,
          'total_rfqs': rfqTotal,
          'pending_actions': 0,
        },
        'recent_pos': poItems,
      };
    } catch (e) {
      // Fallback if any endpoint fails
      return {
        'active_pos': 0,
        'open_invoices': 0,
        'pending_rfqs': 0,
        'pending_prs': 0,
        'stats': {
          'total_pos': 0,
          'total_invoices': 0,
          'total_rfqs': 0,
          'pending_actions': 0,
        },
        'recent_pos': [],
      };
    }
  }

  // ─── Purchase Orders (/api/v1 prefix) ──────────────────
  Future<Map<String, dynamic>> getPurchaseOrders({
    String? status,
    int page = 1,
    int limit = 20,
  }) async {
    final resp = await dio.get(
      '/api/v1/purchase-orders',
      queryParameters: {
        'page': page,
        'limit': limit,
        if (status != null) 'status': status,
      },
    );
    return resp.data;
  }

  Future<Map<String, dynamic>> getPurchaseOrder(String id) async {
    final resp = await dio.get('/api/v1/purchase-orders/$id');
    return resp.data;
  }

  Future<Map<String, dynamic>> acknowledgePO(
    String id,
    String expectedDeliveryDate,
  ) async {
    final resp = await dio.post(
      '/api/v1/purchase-orders/$id/acknowledge',
      data: {'expected_delivery_date': expectedDeliveryDate},
    );
    return resp.data;
  }

  // ─── RFQs ─────────────────────────────────────────────
  Future<Map<String, dynamic>> getRFQs({
    String? status,
    int page = 1,
    int limit = 20,
  }) async {
    final resp = await dio.get(
      '/api/v1/rfqs',
      queryParameters: {
        'page': page,
        'limit': limit,
        if (status != null) 'status': status,
      },
    );
    return resp.data;
  }

  Future<Map<String, dynamic>> getRFQ(String id) async {
    final resp = await dio.get('/api/v1/rfqs/$id');
    return resp.data;
  }

  Future<Map<String, dynamic>> submitBid(
    String rfqId,
    Map<String, dynamic> bidData,
  ) async {
    final resp = await dio.post('/api/v1/rfqs/$rfqId/bids', data: bidData);
    return resp.data;
  }

  // ─── Invoices ─────────────────────────────────────────
  Future<Map<String, dynamic>> getInvoices({
    String? status,
    int page = 1,
    int limit = 20,
  }) async {
    final resp = await dio.get(
      '/api/v1/invoices',
      queryParameters: {
        'page': page,
        'limit': limit,
        if (status != null) 'status': status,
      },
    );
    return resp.data;
  }

  Future<Map<String, dynamic>> createInvoice({
    required String poId,
    required String invoiceNumber,
    required String invoiceDate, // YYYY-MM-DD
    required int totalCents,
    String? documentKey,
  }) async {
    final data = Map<String, dynamic>.from({
      'po_id': poId,
      'invoice_number': invoiceNumber,
      'invoice_date': invoiceDate,
      'total_cents': totalCents,
      if (documentKey != null) 'document_key': documentKey,
    });
    final resp = await dio.post('/api/v1/invoices', data: data);
    return resp.data;
  }

  // ─── Files ────────────────────────────────────────────
  Future<Map<String, dynamic>> uploadFile(String filePath) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath),
    });
    final resp = await dio.post('/api/v1/files/upload', data: formData);
    return resp.data;
  }

  // ─── Vendors / Users ──────────────────────────────────
  Future<Map<String, dynamic>> getVendorMe() async {
    final resp = await dio.get('/api/v1/vendors/me');
    return resp.data;
  }

  Future<Map<String, dynamic>> getMe() async {
    final resp = await dio.get('/api/v1/users/me');
    return resp.data;
  }

  Future<Map<String, dynamic>> updateProfile(Map<String, dynamic> data) async {
    final me = await getMe();
    final userId = me['id'];
    final resp = await dio.put('/api/v1/users/$userId', data: data);
    return resp.data;
  }

  Future<void> changePassword(
    String currentPassword,
    String newPassword,
  ) async {
    await dio.post(
      '/api/v1/auth/change-password',
      data: {'current_password': currentPassword, 'new_password': newPassword},
    );
  }

  // ─── FCM ──────────────────────────────────────────────
  Future<void> updateFCMToken(String token, String deviceType) async {
    await dio.post(
      '/api/v1/users/me/devices',
      data: {'fcm_token': token, 'device_type': deviceType},
    );
  }
}
