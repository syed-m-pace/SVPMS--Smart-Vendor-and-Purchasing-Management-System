import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/currency_formatter.dart';
import '../../widgets/status_badge.dart';
import '../bloc/invoice_bloc.dart';

class InvoiceListScreen extends StatelessWidget {
  const InvoiceListScreen({super.key});

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
          if (state.invoices.isEmpty) {
            return Center(
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
            );
          }
          return RefreshIndicator(
            onRefresh: () async =>
                context.read<InvoiceBloc>().add(LoadInvoices()),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: state.invoices.length,
              itemBuilder: (context, i) {
                final inv = state.invoices[i];
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    title: Text(
                      inv.invoiceNumber,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(
                      '${formatCurrency(inv.totalCents)} • PO: ${inv.poNumber ?? "N/A"}',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                    trailing: StatusBadge(status: inv.status),
                  ),
                );
              },
            ),
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
