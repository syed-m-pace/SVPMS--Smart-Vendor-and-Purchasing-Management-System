import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:svpms_vendor/app.dart';
import 'package:svpms_vendor/services/local_cache_service.dart';
import 'package:svpms_vendor/services/storage_service.dart';
import 'package:svpms_vendor/data/repositories/auth_repository.dart';
import 'package:svpms_vendor/data/models/user.dart';
import 'package:mockito/mockito.dart';

import 'robots/auth_robot.dart';
import 'robots/dashboard_robot.dart';

// Create a Mock class for LocalCacheService
class MockLocalCacheService extends Mock implements LocalCacheService {
  @override
  Future<void> init() async {
    return Future.value();
  }
}

// Create a Mock class for StorageService
class MockStorageService extends Mock implements StorageService {
  @override
  Future<bool> get hasTokens => super.noSuchMethod(
    Invocation.getter(#hasTokens),
    returnValue: Future.value(false),
    returnValueForMissingStub: Future.value(false),
  );

  @override
  Future<String?> get accessToken => super.noSuchMethod(
    Invocation.getter(#accessToken),
    returnValue: Future.value(null),
    returnValueForMissingStub: Future.value(null),
  );

  @override
  Future<String?> get refreshToken => super.noSuchMethod(
    Invocation.getter(#refreshToken),
    returnValue: Future.value(null),
    returnValueForMissingStub: Future.value(null),
  );

  @override
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) {
    return super.noSuchMethod(
      Invocation.method(#saveTokens, [], {
        #accessToken: accessToken,
        #refreshToken: refreshToken,
      }),
      returnValue: Future.value(),
      returnValueForMissingStub: Future.value(),
    );
  }

  @override
  Future<void> clearTokens() {
    return super.noSuchMethod(
      Invocation.method(#clearTokens, []),
      returnValue: Future.value(),
      returnValueForMissingStub: Future.value(),
    );
  }
}

// Create a Mock class for AuthRepository
class MockAuthRepository extends Mock implements AuthRepository {
  @override
  Future<User> login(String email, String password) {
    if (email == 'vendor@alphasupplies.com' && password == 'wrongpassword') {
      throw Exception('Invalid email or password');
    }
    if (email == 'admin@acme.com' && password == 'SvpmsTest123!') {
      return Future.value(
        User(
          id: 'admin',
          email: 'admin@acme.com',
          firstName: 'Admin',
          lastName: 'User',
          role: 'admin',
        ),
      );
    }
    if (email == 'vendor@alphasupplies.com' && password == 'SvpmsTest123!') {
      return Future.value(
        User(
          id: 'vendor',
          email: 'vendor@alphasupplies.com',
          firstName: 'Vendor',
          lastName: 'User',
          role: 'vendor',
        ),
      );
    }
    throw Exception('User not found');
  }

  @override
  Future<void> logout() {
    return Future.value();
  }

  @override
  Future<bool> isAuthenticated() {
    return Future.value(false);
  }
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('E2E Vendor Flow', () {
    testWidgets('Login with invalid, forbidden, and valid credentials', (
      tester,
    ) async {
      debugPrint('STEP: Starting test');
      try {
        // 1. Setup mocks
        final mockCache = MockLocalCacheService();
        final mockStorage = MockStorageService();
        final mockAuthRepo = MockAuthRepository();

        // 2. Initialize app directly with mocked dependencies
        debugPrint('STEP: Pump widget');
        await tester.pumpWidget(
          SVPMSApp(
            localCache: mockCache,
            storageService: mockStorage,
            authRepository: mockAuthRepo,
          ),
        );
        await tester.pumpAndSettle();

        final authRobot = AuthRobot(tester);
        final dashboardRobot = DashboardRobot(tester);

        // 3. Login with Invalid Credentials
        debugPrint('STEP: Login invalid');
        await authRobot.login('vendor@alphasupplies.com', 'wrongpassword');
        await authRobot.verifyErrorDisplayed('Invalid email or password');

        // 4. Login with Forbidden User (Admin)
        debugPrint('STEP: Login forbidden');
        await authRobot.login('admin@acme.com', 'SvpmsTest123!');
        await authRobot.verifyErrorDisplayed(
          'Access denied: Vendor portal only',
        );

        // 5. Login with Valid Credentials
        debugPrint('STEP: Login valid');
        await authRobot.login('vendor@alphasupplies.com', 'SvpmsTest123!');
        await dashboardRobot.verifyDashboardLoaded();

        debugPrint('STEP: Test complete');
      } catch (e, stack) {
        debugPrint('TEST FAILED: $e');
        debugPrint(stack.toString());
        rethrow;
      }
    });
  });
}
