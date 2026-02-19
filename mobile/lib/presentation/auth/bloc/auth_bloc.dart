import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../../data/models/user.dart';
import '../../../data/repositories/auth_repository.dart';

// ─── Events ──────────────────────────────────────────────
abstract class AuthEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class CheckAuth extends AuthEvent {}

class LoginRequested extends AuthEvent {
  final String email;
  final String password;
  LoginRequested({required this.email, required this.password});
  @override
  List<Object?> get props => [email, password];
}

class LogoutRequested extends AuthEvent {}

class UpdateProfileRequested extends AuthEvent {
  final Map<String, dynamic> data;
  UpdateProfileRequested(this.data);
  @override
  List<Object?> get props => [data];
}

class ChangePasswordRequested extends AuthEvent {
  final String currentPassword;
  final String newPassword;
  ChangePasswordRequested({
    required this.currentPassword,
    required this.newPassword,
  });
  @override
  List<Object?> get props => [currentPassword, newPassword];
}

// ─── States ──────────────────────────────────────────────
abstract class AuthState extends Equatable {
  @override
  List<Object?> get props => [];
}

class AuthInitial extends AuthState {}

class AuthLoading extends AuthState {}

class Authenticated extends AuthState {
  final User user;
  Authenticated(this.user);
  @override
  List<Object?> get props => [user];
}

class Unauthenticated extends AuthState {}

class AuthError extends AuthState {
  final String message;
  AuthError(this.message);
  @override
  List<Object?> get props => [message];
}

// ─── Bloc ────────────────────────────────────────────────
class AuthBloc extends Bloc<AuthEvent, AuthState> {
  final AuthRepository _repo;

  AuthBloc({required AuthRepository repo})
    : _repo = repo,
      super(AuthInitial()) {
    on<CheckAuth>(_onCheckAuth);
    on<LoginRequested>(_onLogin);

    on<LogoutRequested>(_onLogout);
    on<UpdateProfileRequested>(_onUpdateProfile);
    on<ChangePasswordRequested>(_onChangePassword);
  }

  Future<void> _onCheckAuth(CheckAuth event, Emitter<AuthState> emit) async {
    final isAuth = await _repo.isAuthenticated();
    if (isAuth) {
      try {
        final user = await _repo.getMe();
        emit(Authenticated(user));
        await _repo.registerCurrentDeviceToken();
      } catch (_) {
        emit(Unauthenticated());
      }
    } else {
      emit(Unauthenticated());
    }
  }

  Future<void> _onLogin(LoginRequested event, Emitter<AuthState> emit) async {
    emit(AuthLoading());
    try {
      final user = await _repo.login(event.email, event.password);
      if (user.role.toLowerCase() != 'vendor') {
        await _repo.logout();
        emit(AuthError('Access denied: Vendor portal only'));
      } else {
        emit(Authenticated(user));
        await _repo.registerCurrentDeviceToken();
      }
    } catch (e) {
      final msg = e.toString().contains('DioException')
          ? 'Invalid email or password'
          : e.toString().replaceAll('Exception: ', '');
      emit(AuthError(msg));
    }
  }

  Future<void> _onLogout(LogoutRequested event, Emitter<AuthState> emit) async {
    await _repo.logout();
    emit(Unauthenticated());
  }

  Future<void> _onUpdateProfile(
    UpdateProfileRequested event,
    Emitter<AuthState> emit,
  ) async {
    final currentState = state;
    if (currentState is Authenticated) {
      try {
        final updatedUser = await _repo.updateProfile(event.data);
        emit(Authenticated(updatedUser));
      } catch (e) {
        // For now, emit error. UI should handle success/failure feedback via Repository if possible,
        // or listen to this state.
        emit(AuthError('Failed to update profile: $e'));
        // Re-emit authenticated state to restore UI after error
        emit(Authenticated(currentState.user));
      }
    }
  }

  Future<void> _onChangePassword(
    ChangePasswordRequested event,
    Emitter<AuthState> emit,
  ) async {
    final currentState = state;
    if (currentState is! Authenticated) return;

    try {
      await _repo.changePassword(event.currentPassword, event.newPassword);
      // Optional: emit success event or relying on UI optimism?
      // Since password change doesn't alter User object (immediately visible),
      // we just stay Authenticated.
    } catch (e) {
      emit(AuthError('Failed to change password: $e'));
      // Restore state
      emit(Authenticated(currentState.user));
    }
  }
}
