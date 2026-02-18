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

class LoadPODetail extends POEvent {
  final String id;
  LoadPODetail(this.id);
  @override
  List<Object?> get props => [id];
}

class AcknowledgePO extends POEvent {
  final String id;
  AcknowledgePO(this.id);
  @override
  List<Object?> get props => [id];
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
  POListLoaded(this.orders);
  @override
  List<Object?> get props => [orders];
}

class PODetailLoaded extends POState {
  final PurchaseOrder po;
  PODetailLoaded(this.po);
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

  POBloc({required PORepository repo}) : _repo = repo, super(POInitial()) {
    on<LoadPOs>(_onLoadList);
    on<LoadPODetail>(_onLoadDetail);
    on<AcknowledgePO>(_onAcknowledge);
  }

  Future<void> _onLoadList(LoadPOs event, Emitter<POState> emit) async {
    emit(POLoading());
    try {
      final orders = await _repo.list(status: event.status);
      emit(POListLoaded(orders));
    } catch (e) {
      emit(POError(e.toString()));
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
    try {
      final po = await _repo.acknowledge(event.id);
      emit(POAcknowledged(po));
    } catch (e) {
      emit(POError(e.toString()));
    }
  }
}
