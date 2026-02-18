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

  Future<Map<String, dynamic>> getMe() async {
    final resp = await dio.get('/auth/me');
    return resp.data;
  }

  // ─── Dashboard (aggregated from POs + Invoices) ───────
  /// No dedicated dashboard endpoint exists — we aggregate from other APIs
  Future<Map<String, dynamic>> getDashboard() async {
    try {
      final results = await Future.wait([
        dio.get(
          '/api/v1/purchase-orders',
          queryParameters: {'page': 1, 'size': 5},
        ),
        dio.get('/api/v1/invoices', queryParameters: {'page': 1, 'size': 5}),
        dio.get('/api/v1/rfqs', queryParameters: {'page': 1, 'size': 5}),
      ]);

      final poData = results[0].data;
      final invoiceData = results[1].data;
      final rfqData = results[2].data;

      return {
        'stats': {
          'total_pos':
              poData['total'] ?? (poData['items'] as List?)?.length ?? 0,
          'total_invoices':
              invoiceData['total'] ??
              (invoiceData['items'] as List?)?.length ??
              0,
          'total_rfqs':
              rfqData['total'] ?? (rfqData['items'] as List?)?.length ?? 0,
          'pending_actions': 0,
        },
        'recent_pos': poData['items'] ?? [],
      };
    } catch (e) {
      // Fallback if any endpoint fails
      return {
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
    int size = 20,
  }) async {
    final resp = await dio.get(
      '/api/v1/purchase-orders',
      queryParameters: {
        'page': page,
        'size': size,
        if (status != null) 'status': status,
      },
    );
    return resp.data;
  }

  Future<Map<String, dynamic>> getPurchaseOrder(String id) async {
    final resp = await dio.get('/api/v1/purchase-orders/$id');
    return resp.data;
  }

  Future<Map<String, dynamic>> acknowledgePO(String id) async {
    final resp = await dio.post('/api/v1/purchase-orders/$id/acknowledge');
    return resp.data;
  }

  // ─── RFQs ─────────────────────────────────────────────
  Future<Map<String, dynamic>> getRFQs({int page = 1, int size = 20}) async {
    final resp = await dio.get(
      '/api/v1/rfqs',
      queryParameters: {'page': page, 'size': size},
    );
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
    int size = 20,
  }) async {
    final resp = await dio.get(
      '/api/v1/invoices',
      queryParameters: {
        'page': page,
        'size': size,
        if (status != null) 'status': status,
      },
    );
    return resp.data;
  }

  Future<Map<String, dynamic>> uploadInvoice({
    required String poId,
    required String invoiceNumber,
    required String invoiceDate,
    required int totalCents,
    String? filePath,
  }) async {
    final data = FormData.fromMap({
      'po_id': poId,
      'invoice_number': invoiceNumber,
      'invoice_date': invoiceDate,
      'total_cents': totalCents,
      if (filePath != null)
        'file': await MultipartFile.fromFile(filePath, filename: 'invoice.pdf'),
    });
    final resp = await dio.post('/api/v1/invoices', data: data);
    return resp.data;
  }

  // ─── Vendors ──────────────────────────────────────────
  Future<Map<String, dynamic>> getVendorProfile() async {
    final resp = await dio.get('/api/v1/vendors');
    return resp.data;
  }

  // ─── FCM ──────────────────────────────────────────────
  Future<void> updateFCMToken(String token) async {
    await dio.post('/api/v1/users/me/devices', data: {'fcm_token': token});
  }
}
