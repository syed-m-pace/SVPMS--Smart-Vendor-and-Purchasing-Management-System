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
  }

  Future<void> _onCheckAuth(CheckAuth event, Emitter<AuthState> emit) async {
    final isAuth = await _repo.isAuthenticated();
    if (isAuth) {
      try {
        final user = await _repo.getMe();
        emit(Authenticated(user));
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
      if (user.role != 'vendor') {
        await _repo.logout();
        emit(AuthError('Access denied: Vendor portal only'));
      } else {
        emit(Authenticated(user));
      }
    } catch (e) {
      final msg = e.toString().contains('DioException')
          ? 'Invalid email or password'
          : e.toString();
      emit(AuthError(msg));
    }
  }

  Future<void> _onLogout(LogoutRequested event, Emitter<AuthState> emit) async {
    await _repo.logout();
    emit(Unauthenticated());
  }
}
