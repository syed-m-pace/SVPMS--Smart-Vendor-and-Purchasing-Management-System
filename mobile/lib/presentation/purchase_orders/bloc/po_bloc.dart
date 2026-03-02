import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../../data/models/purchase_order.dart';
import '../../../data/repositories/po_repository.dart';

// ─── Events ──────────────────────────────────────────────
abstract class POEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class LoadPOs extends POEvent {
  final String? status;
  LoadPOs({this.status});
  @override
  List<Object?> get props => [status];
}

class LoadMorePOs extends POEvent {}

class RefreshPOs extends POEvent {}

class LoadPODetail extends POEvent {
  final String id;
  LoadPODetail(this.id);
  @override
  List<Object?> get props => [id];
}

class AcknowledgePO extends POEvent {
  final String id;
  final String expectedDeliveryDate;
  AcknowledgePO(this.id, this.expectedDeliveryDate);
  @override
  List<Object?> get props => [id, expectedDeliveryDate];
}

// ─── States ──────────────────────────────────────────────
abstract class POState extends Equatable {
  @override
  List<Object?> get props => [];
}

class POInitial extends POState {}

class POLoading extends POState {}

class POListLoaded extends POState {
  final List<PurchaseOrder> orders;
  final bool hasMore;
  final int page;
  final bool isLoadingMore;
  POListLoaded(this.orders, {this.hasMore = true, this.page = 1, this.isLoadingMore = false});
  @override
  List<Object?> get props => [orders, hasMore, page, isLoadingMore];
}

class PODetailLoaded extends POState {
  final PurchaseOrder po;
  PODetailLoaded(this.po);
  @override
  List<Object?> get props => [po];
}

class POAcknowledging extends POState {
  final PurchaseOrder po;
  POAcknowledging(this.po);
  @override
  List<Object?> get props => [po];
}

class POAcknowledged extends POState {
  final PurchaseOrder po;
  POAcknowledged(this.po);
  @override
  List<Object?> get props => [po];
}

class POError extends POState {
  final String message;
  POError(this.message);
  @override
  List<Object?> get props => [message];
}

// ─── Bloc ────────────────────────────────────────────────
class POBloc extends Bloc<POEvent, POState> {
  final PORepository _repo;
  String? _lastStatus;

  POBloc({required PORepository repo}) : _repo = repo, super(POInitial()) {
    on<LoadPOs>(_onLoadList);
    on<LoadMorePOs>(_onLoadMore);
    on<RefreshPOs>(_onRefresh);
    on<LoadPODetail>(_onLoadDetail);
    on<AcknowledgePO>(_onAcknowledge);
  }

  Future<void> _onLoadList(LoadPOs event, Emitter<POState> emit) async {
    _lastStatus = event.status;
    emit(POLoading());
    try {
      final orders = await _repo.list(status: event.status, page: 1);
      emit(POListLoaded(orders, hasMore: orders.length >= 20, page: 1));
    } catch (e) {
      emit(POError(e.toString()));
    }
  }

  Future<void> _onRefresh(RefreshPOs event, Emitter<POState> emit) async {
    try {
      final orders = await _repo.list(status: _lastStatus, page: 1);
      emit(POListLoaded(orders, hasMore: orders.length >= 20, page: 1));
    } catch (e) {
      emit(POError(e.toString()));
    }
  }

  Future<void> _onLoadMore(LoadMorePOs event, Emitter<POState> emit) async {
    final current = state;
    if (current is! POListLoaded || !current.hasMore || current.isLoadingMore) return;

    emit(POListLoaded(current.orders, hasMore: current.hasMore, page: current.page, isLoadingMore: true));
    try {
      final nextPage = current.page + 1;
      final more = await _repo.list(status: _lastStatus, page: nextPage);
      final combined = [...current.orders, ...more];
      emit(POListLoaded(combined, hasMore: more.length >= 20, page: nextPage));
    } catch (e) {
      emit(POListLoaded(current.orders, hasMore: current.hasMore, page: current.page));
    }
  }

  Future<void> _onLoadDetail(LoadPODetail event, Emitter<POState> emit) async {
    emit(POLoading());
    try {
      final po = await _repo.getById(event.id);
      emit(PODetailLoaded(po));
    } catch (e) {
      emit(POError(e.toString()));
    }
  }

  Future<void> _onAcknowledge(
    AcknowledgePO event,
    Emitter<POState> emit,
  ) async {
    final currentState = state;
    if (currentState is PODetailLoaded) {
      emit(POAcknowledging(currentState.po));
    } else if (currentState is POAcknowledged) {
      emit(POAcknowledging(currentState.po));
    }
    try {
      final po = await _repo.acknowledge(event.id, event.expectedDeliveryDate);
      emit(POAcknowledged(po));
    } catch (e) {
      emit(POError(e.toString()));
    }
  }
}
