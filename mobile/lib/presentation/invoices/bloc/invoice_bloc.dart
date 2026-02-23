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

// ─── States ──────────────────────────────────────────────
abstract class InvoiceState extends Equatable {
  @override
  List<Object?> get props => [];
}

class InvoiceInitial extends InvoiceState {}

class InvoiceLoading extends InvoiceState {}

class InvoiceListLoaded extends InvoiceState {
  final List<Invoice> invoices;
  InvoiceListLoaded(this.invoices);
  @override
  List<Object?> get props => [invoices];
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

// ─── Bloc ────────────────────────────────────────────────
class InvoiceBloc extends Bloc<InvoiceEvent, InvoiceState> {
  final InvoiceRepository _repo;

  InvoiceBloc({required InvoiceRepository repo})
    : _repo = repo,
      super(InvoiceInitial()) {
    on<LoadInvoices>(_onLoad);
    on<UploadInvoice>(_onUpload);
    on<DisputeInvoice>(_onDispute);
  }

  Future<void> _onLoad(LoadInvoices event, Emitter<InvoiceState> emit) async {
    emit(InvoiceLoading());
    try {
      final invoices = await _repo.list(status: event.status);
      emit(InvoiceListLoaded(invoices));
    } catch (e) {
      emit(InvoiceError(e.toString()));
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
}
