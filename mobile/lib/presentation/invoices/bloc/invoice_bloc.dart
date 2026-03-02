import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../../data/models/invoice.dart';
import '../../../data/repositories/invoice_repository.dart';

// ─── Events ──────────────────────────────────────────────
abstract class InvoiceEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class LoadInvoices extends InvoiceEvent {
  final String? status;
  LoadInvoices({this.status});
  @override
  List<Object?> get props => [status];
}

class LoadMoreInvoices extends InvoiceEvent {}

class RefreshInvoices extends InvoiceEvent {}

class UploadInvoice extends InvoiceEvent {
  final String poId;
  final String invoiceNumber;
  final String invoiceDate;
  final int totalCents;
  final String? filePath;
  UploadInvoice({
    required this.poId,
    required this.invoiceNumber,
    required this.invoiceDate,
    required this.totalCents,
    this.filePath,
  });
  @override
  List<Object?> get props => [poId, invoiceNumber, invoiceDate, totalCents];
}

class DisputeInvoice extends InvoiceEvent {
  final String invoiceId;
  final String? reason;
  DisputeInvoice({required this.invoiceId, this.reason});
  @override
  List<Object?> get props => [invoiceId, reason];
}

class ReuploadInvoice extends InvoiceEvent {
  final String invoiceId;
  final String filePath;
  ReuploadInvoice({required this.invoiceId, required this.filePath});
  @override
  List<Object?> get props => [invoiceId, filePath];
}

// ─── States ──────────────────────────────────────────────
abstract class InvoiceState extends Equatable {
  @override
  List<Object?> get props => [];
}

class InvoiceInitial extends InvoiceState {}

class InvoiceLoading extends InvoiceState {}

class InvoiceListLoaded extends InvoiceState {
  final List<Invoice> invoices;
  final bool hasMore;
  final int page;
  final bool isLoadingMore;
  InvoiceListLoaded(this.invoices, {this.hasMore = true, this.page = 1, this.isLoadingMore = false});
  @override
  List<Object?> get props => [invoices, hasMore, page, isLoadingMore];
}

class InvoiceUploaded extends InvoiceState {
  final Invoice invoice;
  InvoiceUploaded(this.invoice);
  @override
  List<Object?> get props => [invoice];
}

class InvoiceError extends InvoiceState {
  final String message;
  InvoiceError(this.message);
  @override
  List<Object?> get props => [message];
}

class InvoiceDisputed extends InvoiceState {
  final Invoice invoice;
  InvoiceDisputed(this.invoice);
  @override
  List<Object?> get props => [invoice];
}

class InvoiceReuploaded extends InvoiceState {
  final Invoice invoice;
  InvoiceReuploaded(this.invoice);
  @override
  List<Object?> get props => [invoice];
}

// ─── Bloc ────────────────────────────────────────────────
class InvoiceBloc extends Bloc<InvoiceEvent, InvoiceState> {
  final InvoiceRepository _repo;
  String? _lastStatus;

  InvoiceBloc({required InvoiceRepository repo})
    : _repo = repo,
      super(InvoiceInitial()) {
    on<LoadInvoices>(_onLoad);
    on<LoadMoreInvoices>(_onLoadMore);
    on<RefreshInvoices>(_onRefresh);
    on<UploadInvoice>(_onUpload);
    on<DisputeInvoice>(_onDispute);
    on<ReuploadInvoice>(_onReupload);
  }

  Future<void> _onLoad(LoadInvoices event, Emitter<InvoiceState> emit) async {
    _lastStatus = event.status;
    emit(InvoiceLoading());
    try {
      final invoices = await _repo.list(status: event.status, page: 1);
      emit(InvoiceListLoaded(invoices, hasMore: invoices.length >= 20, page: 1));
    } catch (e) {
      emit(InvoiceError(e.toString()));
    }
  }

  Future<void> _onRefresh(RefreshInvoices event, Emitter<InvoiceState> emit) async {
    try {
      final invoices = await _repo.list(status: _lastStatus, page: 1);
      emit(InvoiceListLoaded(invoices, hasMore: invoices.length >= 20, page: 1));
    } catch (e) {
      emit(InvoiceError(e.toString()));
    }
  }

  Future<void> _onLoadMore(LoadMoreInvoices event, Emitter<InvoiceState> emit) async {
    final current = state;
    if (current is! InvoiceListLoaded || !current.hasMore || current.isLoadingMore) return;

    emit(InvoiceListLoaded(current.invoices, hasMore: current.hasMore, page: current.page, isLoadingMore: true));
    try {
      final nextPage = current.page + 1;
      final more = await _repo.list(status: _lastStatus, page: nextPage);
      final combined = [...current.invoices, ...more];
      emit(InvoiceListLoaded(combined, hasMore: more.length >= 20, page: nextPage));
    } catch (e) {
      emit(InvoiceListLoaded(current.invoices, hasMore: current.hasMore, page: current.page));
    }
  }

  Future<void> _onUpload(
    UploadInvoice event,
    Emitter<InvoiceState> emit,
  ) async {
    emit(InvoiceLoading());
    try {
      final invoice = await _repo.upload(
        poId: event.poId,
        invoiceNumber: event.invoiceNumber,
        invoiceDate: event.invoiceDate,
        totalCents: event.totalCents,
        filePath: event.filePath,
      );
      emit(InvoiceUploaded(invoice));
    } catch (e) {
      emit(InvoiceError(e.toString()));
    }
  }

  Future<void> _onDispute(
    DisputeInvoice event,
    Emitter<InvoiceState> emit,
  ) async {
    emit(InvoiceLoading());
    try {
      final invoice = await _repo.disputeInvoice(
        event.invoiceId,
        reason: event.reason,
      );
      emit(InvoiceDisputed(invoice));
    } catch (e) {
      emit(InvoiceError(e.toString()));
    }
  }

  Future<void> _onReupload(
    ReuploadInvoice event,
    Emitter<InvoiceState> emit,
  ) async {
    emit(InvoiceLoading());
    try {
      final invoice = await _repo.reuploadInvoice(
        event.invoiceId,
        event.filePath,
      );
      emit(InvoiceReuploaded(invoice));
    } catch (e) {
      emit(InvoiceError(e.toString()));
    }
  }
}
