import 'package:dio/dio.dart';
import '../datasources/api/api_client.dart';
import '../models/user.dart';
import '../../services/storage_service.dart';
import '../../services/local_cache_service.dart';

class AuthRepository {
  final ApiClient _api;
  final StorageService _storage;
  final LocalCacheService _cache;

  AuthRepository({
    required ApiClient api,
    required StorageService storage,
    required LocalCacheService cache,
  }) : _api = api,
       _storage = storage,
       _cache = cache;

  Future<User> login(String email, String password) async {
    final data = await _api.login(email, password);
    await _storage.saveTokens(
      accessToken: data['access_token'],
      refreshToken: data['refresh_token'],
    );
    // Login response doesn't include user — fetch via /auth/me
    return getMe();
  }

  Future<User> getMe() async {
    try {
      final data = await _api.getMe();
      await _cache.cacheUser(data);
      return User.fromJson(data);
    } catch (e) {
      if (e is DioException) {
        final cached = _cache.getCachedUser();
        if (cached != null) return User.fromJson(cached);
      }
      rethrow;
    }
  }

  Future<User> updateProfile(Map<String, dynamic> data) async {
    final responseData = await _api.updateProfile(data);
    // The API returns the updated user object. Update cache.
    await _cache.cacheUser(responseData);
    return User.fromJson(responseData);
  }

  Future<void> changePassword(
    String currentPassword,
    String newPassword,
  ) async {
    await _api.changePassword(currentPassword, newPassword);
  }

  Future<void> logout() async {
    await _storage.clearTokens();
    await _cache.clearCache();
  }

  Future<bool> isAuthenticated() => _storage.hasTokens;
}
