import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:svpms_vendor/services/local_cache_service.dart';

void main() {
  late LocalCacheService service;
  late Directory tempDir;

  setUp(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    tempDir = await Directory.systemTemp.createTemp('hive_test_');

    // Mock path_provider to return our temp directory
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.flutter.io/path_provider'),
      (MethodCall methodCall) async => tempDir.path,
    );
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.flutter.io/path_provider_macos'),
      (MethodCall methodCall) async => tempDir.path,
    );

    service = LocalCacheService();
    await service.init();
  });

  tearDown(() async {
    await Hive.close();
    // Clear mock handlers
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.flutter.io/path_provider'),
      null,
    );
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.flutter.io/path_provider_macos'),
      null,
    );
    if (tempDir.existsSync()) {
      tempDir.deleteSync(recursive: true);
    }
  });

  group('generic cache', () {
    test('cacheData + getCachedData round trip', () async {
      await service.cacheData('test_key', {'hello': 'world'});
      final result = service.getCachedData('test_key');
      expect(result, isNotNull);
      expect(result['hello'], 'world');
    });

    test('getCachedData returns null for missing key', () {
      final result = service.getCachedData('nonexistent');
      expect(result, isNull);
    });
  });

  group('user cache', () {
    test('cacheUser + getCachedUser round trip', () async {
      final userJson = {
        'id': 'u-001',
        'email': 'test@test.com',
        'role': 'vendor',
      };
      await service.cacheUser(userJson);
      final result = service.getCachedUser();
      expect(result, isNotNull);
      expect(result!['email'], 'test@test.com');
    });

    test('getCachedUser returns null when not cached', () {
      expect(service.getCachedUser(), isNull);
    });
  });

  group('dashboard cache', () {
    test('cacheDashboard + getCachedDashboard round trip', () async {
      final json = {'active_pos': 5, 'open_invoices': 3};
      await service.cacheDashboard(json);
      final result = service.getCachedDashboard();
      expect(result, isNotNull);
      expect(result!['active_pos'], 5);
    });

    test('getCachedDashboard returns null when not cached', () {
      expect(service.getCachedDashboard(), isNull);
    });
  });

  group('POs cache', () {
    test('cachePOs + getCachedPOs round trip', () async {
      final poList = [
        {'id': 'po-001', 'po_number': 'PO-001'},
        {'id': 'po-002', 'po_number': 'PO-002'},
      ];
      await service.cachePOs(poList);
      final result = service.getCachedPOs();
      expect(result, isNotNull);
      expect(result!.length, 2);
    });

    test('getCachedPOs returns null when not cached', () {
      expect(service.getCachedPOs(), isNull);
    });
  });

  group('RFQs cache', () {
    test('cacheRFQs + getCachedRFQs round trip', () async {
      await service.cacheRFQs([{'id': 'rfq-001'}]);
      final result = service.getCachedRFQs();
      expect(result, isNotNull);
      expect(result!.length, 1);
    });

    test('getCachedRFQs returns null when not cached', () {
      expect(service.getCachedRFQs(), isNull);
    });
  });

  group('clearCache', () {
    test('clears all cached data', () async {
      await service.cacheUser({'id': 'u-001'});
      await service.cacheDashboard({'active_pos': 5});

      await service.clearCache();

      expect(service.getCachedUser(), isNull);
      expect(service.getCachedDashboard(), isNull);
    });
  });
}
