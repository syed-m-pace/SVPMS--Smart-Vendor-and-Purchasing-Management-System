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
                : state is POAcknowledging
                ? state.po
                : null;

            if (po == null) return const SizedBox();

            return RefreshIndicator(
              onRefresh: () async {
                context.read<POBloc>().add(LoadPODetail(poId));
                await Future.delayed(const Duration(milliseconds: 500));
              },
              child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
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
                          _row('Issued to', po.vendorName ?? 'Vendor'),
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
                        onPressed: state is POAcknowledging
                            ? null
                            : () => _ack(context, po.id),
                        icon: state is POAcknowledging
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.check_circle_outline),
                        label: Text(
                          state is POAcknowledging
                              ? 'Acknowledging...'
                              : 'Acknowledge PO',
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.success,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                      ),
                    ),
                ],
              ),
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
    String? selectedDateStr;
    final confirmedDate = await showDialog<String?>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: const Text('Acknowledge PO'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Please add the expected delivery date to acknowledge this purchase order.',
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Expected Delivery Date:',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  InkWell(
                    onTap: () async {
                      final dt = await showDatePicker(
                        context: context,
                        initialDate: DateTime.now(),
                        firstDate: DateTime.now(),
                        lastDate: DateTime.now().add(
                          const Duration(days: 1000),
                        ),
                      );
                      if (dt != null) {
                        setState(() {
                          // Format to YYYY-MM-DD
                          selectedDateStr =
                              '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}';
                        });
                      }
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 12,
                      ),
                      decoration: BoxDecoration(
                        border: Border.all(color: Colors.grey.shade400),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            selectedDateStr ?? 'Select date...',
                            style: TextStyle(
                              color: selectedDateStr == null
                                  ? Colors.grey.shade600
                                  : Colors.black,
                            ),
                          ),
                          const Icon(
                            Icons.calendar_today,
                            size: 20,
                            color: Colors.grey,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx, null),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: selectedDateStr == null
                      ? null
                      : () => Navigator.pop(ctx, selectedDateStr),
                  child: const Text('Acknowledge'),
                ),
              ],
            );
          },
        );
      },
    );
    if (confirmedDate != null && context.mounted) {
      context.read<POBloc>().add(AcknowledgePO(id, confirmedDate));
    }
  }
}
