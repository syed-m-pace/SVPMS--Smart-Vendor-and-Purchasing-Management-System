import 'package:hive_flutter/hive_flutter.dart';

class LocalCacheService {
  static const String _boxName = 'svpms_cache';
  late Box _box;

  Future<void> init() async {
    await Hive.initFlutter();
    // In a real app, register Adapters here
    // Hive.registerAdapter(UserAdapter());
    // ...
    // For simplicity, we'll store JSON maps
    _box = await Hive.openBox(_boxName);
  }

  // Generic helpers
  Future<void> cacheData(String key, dynamic data) async {
    await _box.put(key, data);
  }

  dynamic getCachedData(String key) {
    return _box.get(key);
  }

  Future<void> clearCache() async {
    await _box.clear();
  }

  // Specific helpers
  Future<void> cacheUser(Map<String, dynamic> userJson) async {
    await cacheData('user_profile', userJson);
  }

  Map<String, dynamic>? getCachedUser() {
    final data = getCachedData('user_profile');
    return data != null ? Map<String, dynamic>.from(data) : null;
  }

  Future<void> cacheDashboard(Map<String, dynamic> dashboardJson) async {
    await cacheData('dashboard_stats', dashboardJson);
  }

  Map<String, dynamic>? getCachedDashboard() {
    final data = getCachedData('dashboard_stats');
    return data != null ? Map<String, dynamic>.from(data) : null;
  }

  // Cache lists
  Future<void> cachePOs(List<dynamic> posJson) async {
    await cacheData('pos_list', posJson);
  }

  List<dynamic>? getCachedPOs() {
    final data = getCachedData('pos_list');
    return data != null ? List<dynamic>.from(data) : null;
  }

  Future<void> cacheRFQs(List<dynamic> rfqsJson) async {
    await cacheData('rfqs_list', rfqsJson);
  }

  List<dynamic>? getCachedRFQs() {
    final data = getCachedData('rfqs_list');
    return data != null ? List<dynamic>.from(data) : null;
  }
}
