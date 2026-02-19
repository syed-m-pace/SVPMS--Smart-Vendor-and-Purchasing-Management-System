import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';

import '../../../data/models/rfq.dart';
import '../../../data/repositories/rfq_repository.dart';

// ─── Events ──────────────────────────────────────────────
abstract class RFQEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class LoadRFQs extends RFQEvent {
  final String? status;
  LoadRFQs({this.status});
  @override
  List<Object?> get props => [status];
}

class RefreshRFQs extends RFQEvent {}

class LoadRFQDetail extends RFQEvent {
  final String rfqId;
  LoadRFQDetail(this.rfqId);
  @override
  List<Object?> get props => [rfqId];
}

class SubmitBid extends RFQEvent {
  final String rfqId;
  final int unitPriceCents;
  final int leadTimeDays;
  final String? comments;
  SubmitBid({
    required this.rfqId,
    required this.unitPriceCents,
    required this.leadTimeDays,
    this.comments,
  });
  @override
  List<Object?> get props => [rfqId, unitPriceCents, leadTimeDays, comments];
}

// ─── States ──────────────────────────────────────────────
abstract class RFQState extends Equatable {
  @override
  List<Object?> get props => [];
}

class RFQInitial extends RFQState {}

class RFQLoading extends RFQState {}

class RFQListLoaded extends RFQState {
  final List<RFQ> rfqs;
  final String? activeStatus;
  RFQListLoaded(this.rfqs, {this.activeStatus});
  @override
  List<Object?> get props => [rfqs, activeStatus];
}

class RFQDetailLoaded extends RFQState {
  final RFQ rfq;
  RFQDetailLoaded(this.rfq);
  @override
  List<Object?> get props => [rfq];
}

class BidSubmitted extends RFQState {}

class RFQError extends RFQState {
  final String message;
  RFQError(this.message);
  @override
  List<Object?> get props => [message];
}

// ─── Bloc ────────────────────────────────────────────────
class RFQBloc extends Bloc<RFQEvent, RFQState> {
  final RFQRepository _repo;

  RFQBloc({required RFQRepository repo}) : _repo = repo, super(RFQInitial()) {
    on<LoadRFQs>(_onLoad);
    on<RefreshRFQs>(_onRefresh);
    on<LoadRFQDetail>(_onLoadDetail);
    on<SubmitBid>(_onSubmitBid);
  }

  Future<void> _onLoad(LoadRFQs event, Emitter<RFQState> emit) async {
    emit(RFQLoading());
    try {
      final rfqs = await _repo.list(status: event.status);
      emit(RFQListLoaded(rfqs, activeStatus: event.status));
    } catch (e) {
      emit(RFQError(e.toString()));
    }
  }

  Future<void> _onRefresh(RefreshRFQs event, Emitter<RFQState> emit) async {
    try {
      final rfqs = await _repo.list();
      emit(RFQListLoaded(rfqs));
    } catch (e) {
      emit(RFQError(e.toString()));
    }
  }

  Future<void> _onLoadDetail(
    LoadRFQDetail event,
    Emitter<RFQState> emit,
  ) async {
    emit(RFQLoading());
    try {
      final rfq = await _repo.getById(event.rfqId);
      emit(RFQDetailLoaded(rfq));
    } catch (e) {
      emit(RFQError(e.toString()));
    }
  }

  Future<void> _onSubmitBid(SubmitBid event, Emitter<RFQState> emit) async {
    emit(RFQLoading());
    try {
      await _repo.submitBid(
        event.rfqId,
        unitPriceCents: event.unitPriceCents,
        leadTimeDays: event.leadTimeDays,
        comments: event.comments,
      );
      emit(BidSubmitted());
    } catch (e) {
      emit(RFQError(e.toString()));
    }
  }
}
