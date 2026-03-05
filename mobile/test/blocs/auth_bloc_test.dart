import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/data/models/user.dart';
import 'package:svpms_vendor/presentation/auth/bloc/auth_bloc.dart';

import '../helpers/mocks.dart';
import '../helpers/fixtures.dart';

void main() {
  late MockAuthRepository mockRepo;

  setUp(() {
    mockRepo = MockAuthRepository();
    // Stub registerCurrentDeviceToken (fire-and-forget, always succeeds)
    when(() => mockRepo.registerCurrentDeviceToken())
        .thenAnswer((_) async {});
  });

  group('AuthBloc', () {
    // ── LoginRequested ──

    blocTest<AuthBloc, AuthState>(
      'emits [AuthLoading, Authenticated] on successful vendor login',
      build: () {
        final user = makeUser();
        when(() => mockRepo.login(any(), any()))
            .thenAnswer((_) async => user);
        return AuthBloc(repo: mockRepo);
      },
      act: (bloc) =>
          bloc.add(LoginRequested(email: 'v@test.com', password: 'pass')),
      expect: () => [
        isA<AuthLoading>(),
        isA<Authenticated>().having((s) => s.user.role, 'role', 'vendor'),
      ],
    );

    blocTest<AuthBloc, AuthState>(
      'emits [AuthLoading, AuthError] when login throws',
      build: () {
        when(() => mockRepo.login(any(), any()))
            .thenThrow(Exception('Invalid email or password'));
        return AuthBloc(repo: mockRepo);
      },
      act: (bloc) =>
          bloc.add(LoginRequested(email: 'v@test.com', password: 'bad')),
      expect: () => [
        isA<AuthLoading>(),
        isA<AuthError>()
            .having((s) => s.message, 'message', contains('Invalid')),
      ],
    );

    blocTest<AuthBloc, AuthState>(
      'emits [AuthLoading, AuthError] when non-vendor user logs in',
      build: () {
        final adminUser = makeUser(role: 'admin');
        when(() => mockRepo.login(any(), any()))
            .thenAnswer((_) async => adminUser);
        when(() => mockRepo.logout()).thenAnswer((_) async {});
        return AuthBloc(repo: mockRepo);
      },
      act: (bloc) =>
          bloc.add(LoginRequested(email: 'admin@test.com', password: 'pass')),
      expect: () => [
        isA<AuthLoading>(),
        isA<AuthError>()
            .having((s) => s.message, 'message', contains('Access denied')),
      ],
      verify: (_) {
        verify(() => mockRepo.logout()).called(1);
      },
    );

    // ── CheckAuth ──

    blocTest<AuthBloc, AuthState>(
      'emits [Authenticated] when user has valid token',
      build: () {
        when(() => mockRepo.isAuthenticated())
            .thenAnswer((_) async => true);
        when(() => mockRepo.getMe())
            .thenAnswer((_) async => makeUser());
        return AuthBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(CheckAuth()),
      expect: () => [
        isA<Authenticated>(),
      ],
    );

    blocTest<AuthBloc, AuthState>(
      'emits [Unauthenticated] when no token exists',
      build: () {
        when(() => mockRepo.isAuthenticated())
            .thenAnswer((_) async => false);
        return AuthBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(CheckAuth()),
      expect: () => [
        isA<Unauthenticated>(),
      ],
    );

    blocTest<AuthBloc, AuthState>(
      'emits [Unauthenticated] when token exists but getMe fails',
      build: () {
        when(() => mockRepo.isAuthenticated())
            .thenAnswer((_) async => true);
        when(() => mockRepo.getMe()).thenThrow(Exception('Unauthorized'));
        return AuthBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(CheckAuth()),
      expect: () => [
        isA<Unauthenticated>(),
      ],
    );

    // ── LogoutRequested ──

    blocTest<AuthBloc, AuthState>(
      'emits [Unauthenticated] on logout',
      build: () {
        when(() => mockRepo.logout()).thenAnswer((_) async {});
        return AuthBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LogoutRequested()),
      expect: () => [
        isA<Unauthenticated>(),
      ],
    );

    // ── UpdateProfileRequested ──

    blocTest<AuthBloc, AuthState>(
      'emits [Authenticated] with updated user on profile update',
      build: () {
        final updatedUser = makeUser(firstName: 'Updated');
        when(() => mockRepo.updateProfile(any()))
            .thenAnswer((_) async => updatedUser);
        return AuthBloc(repo: mockRepo);
      },
      seed: () => Authenticated(makeUser()),
      act: (bloc) =>
          bloc.add(UpdateProfileRequested({'first_name': 'Updated'})),
      expect: () => [
        isA<Authenticated>()
            .having((s) => s.user.firstName, 'firstName', 'Updated'),
      ],
    );

    // ── ChangePasswordRequested ──

    blocTest<AuthBloc, AuthState>(
      'emits nothing on successful password change (stays Authenticated)',
      build: () {
        when(() => mockRepo.changePassword(any(), any()))
            .thenAnswer((_) async {});
        return AuthBloc(repo: mockRepo);
      },
      seed: () => Authenticated(makeUser()),
      act: (bloc) => bloc.add(ChangePasswordRequested(
        currentPassword: 'old',
        newPassword: 'new',
      )),
      expect: () => [],
    );

    blocTest<AuthBloc, AuthState>(
      'emits [AuthError, Authenticated] when password change fails',
      build: () {
        when(() => mockRepo.changePassword(any(), any()))
            .thenThrow(Exception('Wrong password'));
        return AuthBloc(repo: mockRepo);
      },
      seed: () => Authenticated(makeUser()),
      act: (bloc) => bloc.add(ChangePasswordRequested(
        currentPassword: 'wrong',
        newPassword: 'new',
      )),
      expect: () => [
        isA<AuthError>(),
        isA<Authenticated>(),
      ],
    );
  });
}
