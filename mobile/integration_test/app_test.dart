import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/app.dart';
import 'package:svpms_vendor/data/models/user.dart';
import 'package:svpms_vendor/services/local_cache_service.dart';
import 'package:svpms_vendor/services/storage_service.dart';
import 'package:svpms_vendor/data/repositories/auth_repository.dart';

import 'robots/auth_robot.dart';
import 'robots/dashboard_robot.dart';
// PO and Invoice robots available for extended flow tests:
// import 'robots/po_robot.dart';
// import 'robots/invoice_robot.dart';

// ── Mocks using mocktail ──
class MockLocalCacheService extends Mock implements LocalCacheService {}

class MockStorageService extends Mock implements StorageService {}

class MockAuthRepository extends Mock implements AuthRepository {}

// ── Test data ──
final _vendorUser = User(
  id: 'vendor-001',
  email: 'vendor@alphasupplies.com',
  firstName: 'Vendor',
  lastName: 'User',
  role: 'vendor',
  isActive: true,
);

final _adminUser = User(
  id: 'admin-001',
  email: 'admin@acme.com',
  firstName: 'Admin',
  lastName: 'User',
  role: 'admin',
  isActive: true,
);

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  late MockLocalCacheService mockCache;
  late MockStorageService mockStorage;
  late MockAuthRepository mockAuthRepo;

  setUp(() {
    mockCache = MockLocalCacheService();
    mockStorage = MockStorageService();
    mockAuthRepo = MockAuthRepository();

    // Default: unauthenticated
    when(() => mockAuthRepo.isAuthenticated()).thenAnswer((_) async => false);
    when(() => mockAuthRepo.logout()).thenAnswer((_) async {});

    // Storage stubs for ApiClient
    when(() => mockStorage.accessToken).thenAnswer((_) async => null);
    when(() => mockStorage.refreshToken).thenAnswer((_) async => null);
    when(() => mockStorage.hasTokens).thenAnswer((_) async => false);
    when(() => mockStorage.saveTokens(
          accessToken: any(named: 'accessToken'),
          refreshToken: any(named: 'refreshToken'),
        )).thenAnswer((_) async {});
    when(() => mockStorage.clearTokens()).thenAnswer((_) async {});
  });

  Widget buildApp() => SVPMSApp(
        localCache: mockCache,
        storageService: mockStorage,
        authRepository: mockAuthRepo,
      );

  group('Authentication', () {
    testWidgets('shows login screen when not authenticated', (tester) async {
      await tester.pumpWidget(buildApp());
      final authRobot = AuthRobot(tester);
      await authRobot.verifyLoginScreenVisible();
    });

    testWidgets('shows error on invalid credentials', (tester) async {
      when(() => mockAuthRepo.login('vendor@alphasupplies.com', 'wrongpassword'))
          .thenThrow(Exception('Invalid email or password'));

      await tester.pumpWidget(buildApp());
      final authRobot = AuthRobot(tester);
      await authRobot.login('vendor@alphasupplies.com', 'wrongpassword');
      await authRobot.verifyErrorDisplayed('Invalid email or password');
    });

    testWidgets('rejects non-vendor (admin) login', (tester) async {
      when(() => mockAuthRepo.login('admin@acme.com', 'SvpmsTest123!'))
          .thenAnswer((_) async => _adminUser);

      await tester.pumpWidget(buildApp());
      final authRobot = AuthRobot(tester);
      await authRobot.login('admin@acme.com', 'SvpmsTest123!');
      await authRobot.verifyErrorDisplayed('Access denied: Vendor portal only');
    });

    testWidgets('successful vendor login navigates to dashboard', (tester) async {
      when(() => mockAuthRepo.login('vendor@alphasupplies.com', 'SvpmsTest123!'))
          .thenAnswer((_) async => _vendorUser);

      await tester.pumpWidget(buildApp());
      final authRobot = AuthRobot(tester);
      final dashboardRobot = DashboardRobot(tester);

      await authRobot.login('vendor@alphasupplies.com', 'SvpmsTest123!');
      await dashboardRobot.verifyDashboardLoaded();
    });
  });
}
