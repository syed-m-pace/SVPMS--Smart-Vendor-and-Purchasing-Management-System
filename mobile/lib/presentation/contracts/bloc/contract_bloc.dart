import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../../data/models/contract.dart';
import '../../../data/repositories/contract_repository.dart';

// ─── Events ──────────────────────────────────────────────
abstract class ContractEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class LoadContracts extends ContractEvent {
  final String? status;
  LoadContracts({this.status});
  @override
  List<Object?> get props => [status];
}

class LoadMoreContracts extends ContractEvent {}

class RefreshContracts extends ContractEvent {}

class LoadContractDetail extends ContractEvent {
  final String id;
  LoadContractDetail(this.id);
  @override
  List<Object?> get props => [id];
}

// ─── States ──────────────────────────────────────────────
abstract class ContractState extends Equatable {
  @override
  List<Object?> get props => [];
}

class ContractInitial extends ContractState {}

class ContractLoading extends ContractState {}

class ContractListLoaded extends ContractState {
  final List<Contract> contracts;
  final bool hasMore;
  final int page;
  final bool isLoadingMore;
  ContractListLoaded(this.contracts, {this.hasMore = true, this.page = 1, this.isLoadingMore = false});
  @override
  List<Object?> get props => [contracts, hasMore, page, isLoadingMore];
}

class ContractDetailLoaded extends ContractState {
  final Contract contract;
  ContractDetailLoaded(this.contract);
  @override
  List<Object?> get props => [contract];
}

class ContractError extends ContractState {
  final String message;
  ContractError(this.message);
  @override
  List<Object?> get props => [message];
}

// ─── Bloc ────────────────────────────────────────────────
class ContractBloc extends Bloc<ContractEvent, ContractState> {
  final ContractRepository _repo;
  String? _lastStatus;

  ContractBloc({required ContractRepository repo})
      : _repo = repo,
        super(ContractInitial()) {
    on<LoadContracts>(_onLoadList);
    on<LoadMoreContracts>(_onLoadMore);
    on<RefreshContracts>(_onRefresh);
    on<LoadContractDetail>(_onLoadDetail);
  }

  Future<void> _onLoadList(
    LoadContracts event,
    Emitter<ContractState> emit,
  ) async {
    _lastStatus = event.status;
    emit(ContractLoading());
    try {
      final contracts = await _repo.list(status: event.status, page: 1);
      emit(ContractListLoaded(contracts, hasMore: contracts.length >= 20, page: 1));
    } catch (e) {
      emit(ContractError(e.toString()));
    }
  }

  Future<void> _onRefresh(
    RefreshContracts event,
    Emitter<ContractState> emit,
  ) async {
    try {
      final contracts = await _repo.list(status: _lastStatus, page: 1);
      emit(ContractListLoaded(contracts, hasMore: contracts.length >= 20, page: 1));
    } catch (e) {
      emit(ContractError(e.toString()));
    }
  }

  Future<void> _onLoadMore(
    LoadMoreContracts event,
    Emitter<ContractState> emit,
  ) async {
    final current = state;
    if (current is! ContractListLoaded || !current.hasMore || current.isLoadingMore) return;

    emit(ContractListLoaded(current.contracts, hasMore: current.hasMore, page: current.page, isLoadingMore: true));
    try {
      final nextPage = current.page + 1;
      final more = await _repo.list(status: _lastStatus, page: nextPage);
      final combined = [...current.contracts, ...more];
      emit(ContractListLoaded(combined, hasMore: more.length >= 20, page: nextPage));
    } catch (e) {
      emit(ContractListLoaded(current.contracts, hasMore: current.hasMore, page: current.page));
    }
  }

  Future<void> _onLoadDetail(
    LoadContractDetail event,
    Emitter<ContractState> emit,
  ) async {
    emit(ContractLoading());
    try {
      final contract = await _repo.getById(event.id);
      emit(ContractDetailLoaded(contract));
    } catch (e) {
      emit(ContractError(e.toString()));
    }
  }
}
