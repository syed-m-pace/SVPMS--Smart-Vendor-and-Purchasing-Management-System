import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/currency_formatter.dart';
import '../../widgets/status_badge.dart';
import '../bloc/invoice_bloc.dart';

class InvoiceListScreen extends StatefulWidget {
  const InvoiceListScreen({super.key});

  @override
  State<InvoiceListScreen> createState() => _InvoiceListScreenState();
}

class _InvoiceListScreenState extends State<InvoiceListScreen> {
  String _statusFilter = 'ALL';
  static const _statuses = ['ALL', 'UPLOADED', 'MATCHED', 'EXCEPTION', 'DISPUTED', 'APPROVED', 'PAID'];

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<InvoiceBloc, InvoiceState>(
      builder: (context, state) {
        if (state is InvoiceLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        if (state is InvoiceError) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(state.message),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () =>
                      context.read<InvoiceBloc>().add(LoadInvoices()),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }
        if (state is InvoiceListLoaded) {
          final filtered = _statusFilter == 'ALL'
              ? state.invoices
              : state.invoices
                  .where((inv) => inv.status.toUpperCase() == _statusFilter)
                  .toList();

          return Column(
            children: [
              // Status filter chips
              SizedBox(
                height: 48,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  children: _statuses.map((s) {
                    final selected = _statusFilter == s;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: FilterChip(
                        label: Text(s),
                        selected: selected,
                        onSelected: (_) => setState(() => _statusFilter = s),
                        selectedColor: AppColors.primary.withValues(alpha: 0.15),
                        checkmarkColor: AppColors.primary,
                        labelStyle: TextStyle(
                          fontSize: 12,
                          color: selected ? AppColors.primary : AppColors.textSecondary,
                          fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              // List
              Expanded(
                child: filtered.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.receipt_long_outlined,
                              size: 64,
                              color: AppColors.textMuted,
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'No invoices',
                              style: TextStyle(
                                fontSize: 16,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: () async =>
                            context.read<InvoiceBloc>().add(LoadInvoices()),
                        child: ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: filtered.length,
                          itemBuilder: (context, i) {
                            final inv = filtered[i];
                            return Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                title: Text(
                                  inv.invoiceNumber,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w600),
                                ),
                                subtitle: Text(
                                  '${formatCurrency(inv.totalCents)} • PO: ${inv.poNumber ?? "N/A"}',
                                  style:
                                      TextStyle(color: AppColors.textSecondary),
                                ),
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    StatusBadge(status: inv.status),
                                    const SizedBox(width: 4),
                                    const Icon(Icons.chevron_right,
                                        color: Colors.grey),
                                  ],
                                ),
                                onTap: () =>
                                    context.push('/invoices/${inv.id}'),
                              ),
                            );
                          },
                        ),
                      ),
              ),
            ],
          );
        }
        if (state is InvoiceUploaded) {
          return const Center(child: CircularProgressIndicator());
        }
        return const SizedBox();
      },
    );
  }
}
