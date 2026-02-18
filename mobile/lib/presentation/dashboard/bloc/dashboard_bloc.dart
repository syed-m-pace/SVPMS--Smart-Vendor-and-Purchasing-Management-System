import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../../data/models/dashboard_stats.dart';
import '../../../data/models/purchase_order.dart';
import '../../../data/repositories/dashboard_repository.dart';

// ─── Events ──────────────────────────────────────────────
abstract class DashboardEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class LoadDashboard extends DashboardEvent {}

class RefreshDashboard extends DashboardEvent {}

// ─── States ──────────────────────────────────────────────
abstract class DashboardState extends Equatable {
  @override
  List<Object?> get props => [];
}

class DashboardInitial extends DashboardState {}

class DashboardLoading extends DashboardState {}

class DashboardLoaded extends DashboardState {
  final DashboardStats stats;
  final List<PurchaseOrder> recentPOs;
  DashboardLoaded({required this.stats, required this.recentPOs});
  @override
  List<Object?> get props => [stats, recentPOs];
}

class DashboardError extends DashboardState {
  final String message;
  DashboardError(this.message);
  @override
  List<Object?> get props => [message];
}

// ─── Bloc ────────────────────────────────────────────────
class DashboardBloc extends Bloc<DashboardEvent, DashboardState> {
  final DashboardRepository _repo;

  DashboardBloc({required DashboardRepository repo})
    : _repo = repo,
      super(DashboardInitial()) {
    on<LoadDashboard>(_onLoad);
    on<RefreshDashboard>(_onRefresh);
  }

  Future<void> _onLoad(
    LoadDashboard event,
    Emitter<DashboardState> emit,
  ) async {
    emit(DashboardLoading());
    try {
      final results = await Future.wait([
        _repo.getStats(),
        _repo.getRecentPOs(),
      ]);
      emit(
        DashboardLoaded(
          stats: results[0] as DashboardStats,
          recentPOs: results[1] as List<PurchaseOrder>,
        ),
      );
    } catch (e) {
      emit(DashboardError(e.toString()));
    }
  }

  Future<void> _onRefresh(
    RefreshDashboard event,
    Emitter<DashboardState> emit,
  ) async {
    try {
      final results = await Future.wait([
        _repo.getStats(),
        _repo.getRecentPOs(),
      ]);
      emit(
        DashboardLoaded(
          stats: results[0] as DashboardStats,
          recentPOs: results[1] as List<PurchaseOrder>,
        ),
      );
    } catch (e) {
      emit(DashboardError(e.toString()));
    }
  }
}
