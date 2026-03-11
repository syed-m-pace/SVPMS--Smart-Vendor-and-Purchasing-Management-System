import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/services/storage_service.dart';

void main() {
  late StorageService service;
  final Map<String, String?> store = {};

  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();

    // Mock the FlutterSecureStorage platform channel
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      (MethodCall methodCall) async {
        final args = methodCall.arguments as Map?;
        final key = args?['key'] as String?;
        switch (methodCall.method) {
          case 'write':
            store[key!] = args?['value'] as String?;
            return null;
          case 'read':
            return store[key];
          case 'delete':
            store.remove(key);
            return null;
          case 'readAll':
            return store;
          default:
            return null;
        }
      },
    );

    store.clear();
    service = StorageService();
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      null,
    );
  });

  group('saveTokens', () {
    test('writes both tokens', () async {
      await service.saveTokens(accessToken: 'at-123', refreshToken: 'rt-456');
      expect(store['access_token'], 'at-123');
      expect(store['refresh_token'], 'rt-456');
    });
  });

  group('accessToken', () {
    test('reads access token', () async {
      store['access_token'] = 'my-token';
      final token = await service.accessToken;
      expect(token, 'my-token');
    });

    test('returns null when not set', () async {
      final token = await service.accessToken;
      expect(token, isNull);
    });
  });

  group('refreshToken', () {
    test('reads refresh token', () async {
      store['refresh_token'] = 'rt-token';
      final token = await service.refreshToken;
      expect(token, 'rt-token');
    });
  });

  group('clearTokens', () {
    test('deletes both tokens', () async {
      store['access_token'] = 'at';
      store['refresh_token'] = 'rt';
      await service.clearTokens();
      expect(store.containsKey('access_token'), false);
      expect(store.containsKey('refresh_token'), false);
    });
  });

  group('hasTokens', () {
    test('returns true when token exists', () async {
      store['access_token'] = 'valid-token';
      expect(await service.hasTokens, true);
    });

    test('returns false when token is null', () async {
      expect(await service.hasTokens, false);
    });

    test('returns false when token is empty', () async {
      store['access_token'] = '';
      expect(await service.hasTokens, false);
    });
  });
}
