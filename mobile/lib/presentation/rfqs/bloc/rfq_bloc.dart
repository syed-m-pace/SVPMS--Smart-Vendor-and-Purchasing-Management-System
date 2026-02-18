import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../../data/models/rfq.dart';
import '../../../data/datasources/api/api_client.dart';

// ─── Events ──────────────────────────────────────────────
abstract class RFQEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class LoadRFQs extends RFQEvent {}

class SubmitBid extends RFQEvent {
  final String rfqId;
  final Map<String, dynamic> bidData;
  SubmitBid({required this.rfqId, required this.bidData});
  @override
  List<Object?> get props => [rfqId, bidData];
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
  RFQListLoaded(this.rfqs);
  @override
  List<Object?> get props => [rfqs];
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
  final ApiClient _api;

  RFQBloc({required ApiClient api}) : _api = api, super(RFQInitial()) {
    on<LoadRFQs>(_onLoad);
    on<SubmitBid>(_onSubmitBid);
  }

  Future<void> _onLoad(LoadRFQs event, Emitter<RFQState> emit) async {
    emit(RFQLoading());
    try {
      final data = await _api.getRFQs();
      final items = data['items'] as List<dynamic>? ?? [];
      final rfqs = items
          .map((e) => RFQ.fromJson(e as Map<String, dynamic>))
          .toList();
      emit(RFQListLoaded(rfqs));
    } catch (e) {
      emit(RFQError(e.toString()));
    }
  }

  Future<void> _onSubmitBid(SubmitBid event, Emitter<RFQState> emit) async {
    emit(RFQLoading());
    try {
      await _api.submitBid(event.rfqId, event.bidData);
      emit(BidSubmitted());
    } catch (e) {
      emit(RFQError(e.toString()));
    }
  }
}
