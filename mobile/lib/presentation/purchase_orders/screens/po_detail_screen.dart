import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/currency_formatter.dart';
import '../../../core/utils/date_formatter.dart';
import '../../../data/repositories/po_repository.dart';
import '../../widgets/status_badge.dart';
import '../bloc/po_bloc.dart';

class PODetailScreen extends StatelessWidget {
  final String poId;
  const PODetailScreen({super.key, required this.poId});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) =>
          POBloc(repo: context.read<PORepository>())..add(LoadPODetail(poId)),
      child: Scaffold(
        appBar: AppBar(title: const Text('Purchase Order')),
        body: BlocConsumer<POBloc, POState>(
          listener: (context, state) {
            if (state is POAcknowledged) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('PO acknowledged successfully'),
                  backgroundColor: AppColors.success,
                ),
              );
            }
          },
          builder: (context, state) {
            if (state is POLoading) {
              return const Center(child: CircularProgressIndicator());
            }
            if (state is POError) {
              return Center(child: Text(state.message));
            }

            final po = state is PODetailLoaded
                ? state.po
                : state is POAcknowledged
                ? state.po
                : null;

            if (po == null) return const SizedBox();

            return SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Header card ──
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                'PO #${po.poNumber}',
                                style: const TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              StatusBadge(status: po.status),
                            ],
                          ),
                          const Divider(height: 24),
                          _row('Issued', formatDate(po.issuedAt)),
                          _row(
                            'Expected Delivery',
                            formatDate(po.expectedDeliveryDate),
                          ),
                          _row('Total', formatCurrency(po.totalCents)),
                          _row('Currency', po.currency),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ── Line items ──
                  if (po.lineItems.isNotEmpty) ...[
                    const Text(
                      'Line Items',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ...po.lineItems.map(
                      (item) => Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          title: Text(item.description),
                          subtitle: Text(
                            'Qty: ${item.quantity} × ${formatCurrency(item.unitPriceCents)}',
                          ),
                          trailing: Text(
                            formatCurrency(
                              (item.quantity * item.unitPriceCents).toInt(),
                            ),
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: 24),

                  // ── Acknowledge button ──
                  if (po.status.toUpperCase() == 'ISSUED')
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: () => _ack(context, po.id),
                        icon: const Icon(Icons.check_circle_outline),
                        label: const Text('Acknowledge PO'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.success,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                      ),
                    ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: AppColors.textSecondary)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  void _ack(BuildContext context, String id) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Acknowledge PO'),
        content: const Text(
          'Are you sure you want to acknowledge this purchase order?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Acknowledge'),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      context.read<POBloc>().add(AcknowledgePO(id));
    }
  }
}
