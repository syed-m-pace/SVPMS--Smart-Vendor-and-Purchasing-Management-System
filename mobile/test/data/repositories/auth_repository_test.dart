import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/data/models/user.dart';
import 'package:svpms_vendor/data/repositories/auth_repository.dart';
import '../../helpers/mocks.dart';
import '../../helpers/fixtures.dart';

void main() {
  late MockApiClient mockApi;
  late MockStorageService mockStorage;
  late MockLocalCacheService mockCache;
  late AuthRepository repo;

  setUp(() {
    mockApi = MockApiClient();
    mockStorage = MockStorageService();
    mockCache = MockLocalCacheService();
    repo = AuthRepository(api: mockApi, storage: mockStorage, cache: mockCache);
  });

  group('login', () {
    test('saves tokens, fetches profile, returns user', () async {
      when(() => mockApi.login('a@b.com', 'pass')).thenAnswer(
        (_) async => {'access_token': 'at', 'refresh_token': 'rt'},
      );
      when(() => mockStorage.saveTokens(accessToken: 'at', refreshToken: 'rt'))
          .thenAnswer((_) async {});
      when(() => mockApi.getMe()).thenAnswer((_) async => makeUserJson());
      when(() => mockCache.cacheUser(any())).thenAnswer((_) async {});

      final user = await repo.login('a@b.com', 'pass');
      expect(user, isA<User>());
      expect(user.email, 'vendor@test.com');
      verify(() => mockStorage.saveTokens(accessToken: 'at', refreshToken: 'rt')).called(1);
    });

    test('clears tokens and cache on error, rethrows', () async {
      when(() => mockApi.login(any(), any())).thenThrow(Exception('fail'));
      when(() => mockStorage.clearTokens()).thenAnswer((_) async {});
      when(() => mockCache.clearCache()).thenAnswer((_) async {});

      expect(() => repo.login('a@b.com', 'bad'), throwsA(isA<Exception>()));
    });
  });

  group('getMe', () {
    test('fetches from API and caches', () async {
      final json = makeUserJson();
      when(() => mockApi.getMe()).thenAnswer((_) async => json);
      when(() => mockCache.cacheUser(json)).thenAnswer((_) async {});

      final user = await repo.getMe();
      expect(user.email, 'vendor@test.com');
      verify(() => mockCache.cacheUser(json)).called(1);
    });

    test('falls back to cache on DioException', () async {
      when(() => mockApi.getMe()).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/me')),
      );
      when(() => mockCache.getCachedUser()).thenReturn(makeUserJson());

      final user = await repo.getMe();
      expect(user.email, 'vendor@test.com');
    });

    test('rethrows when no cache available', () async {
      when(() => mockApi.getMe()).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/me')),
      );
      when(() => mockCache.getCachedUser()).thenReturn(null);

      expect(() => repo.getMe(), throwsA(isA<DioException>()));
    });
  });

  group('updateProfile', () {
    test('calls API and returns updated user', () async {
      final json = makeUserJson(firstName: 'Updated');
      when(() => mockApi.updateProfile(any())).thenAnswer((_) async => json);
      when(() => mockCache.cacheUser(json)).thenAnswer((_) async {});

      final user = await repo.updateProfile({'first_name': 'Updated'});
      expect(user.firstName, 'Updated');
    });
  });

  group('changePassword', () {
    test('delegates to API', () async {
      when(() => mockApi.changePassword('old', 'new'))
          .thenAnswer((_) async {});

      await repo.changePassword('old', 'new');
      verify(() => mockApi.changePassword('old', 'new')).called(1);
    });
  });

  group('logout', () {
    test('clears tokens and cache', () async {
      when(() => mockStorage.clearTokens()).thenAnswer((_) async {});
      when(() => mockCache.clearCache()).thenAnswer((_) async {});

      await repo.logout();
      verify(() => mockStorage.clearTokens()).called(1);
      verify(() => mockCache.clearCache()).called(1);
    });
  });

  group('isAuthenticated', () {
    test('returns true when tokens exist', () async {
      when(() => mockStorage.hasTokens).thenAnswer((_) async => true);
      expect(await repo.isAuthenticated(), true);
    });

    test('returns false when no tokens', () async {
      when(() => mockStorage.hasTokens).thenAnswer((_) async => false);
      expect(await repo.isAuthenticated(), false);
    });
  });
}
