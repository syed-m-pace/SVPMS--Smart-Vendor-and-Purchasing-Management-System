import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/currency_formatter.dart';
import '../../../core/utils/date_formatter.dart';
import '../../../data/repositories/rfq_repository.dart';
import '../../widgets/status_badge.dart';
import '../bloc/rfq_bloc.dart';

class RFQDetailScreen extends StatelessWidget {
  final String rfqId;
  const RFQDetailScreen({super.key, required this.rfqId});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) =>
          RFQBloc(repo: context.read<RFQRepository>())..add(LoadRFQDetail(rfqId)),
      child: Scaffold(
        appBar: AppBar(title: const Text('RFQ Details')),
        body: BlocConsumer<RFQBloc, RFQState>(
          listener: (context, state) {
            if (state is BidSubmitted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Bid submitted successfully!'),
                  backgroundColor: AppColors.success,
                ),
              );
              context.read<RFQBloc>().add(LoadRFQDetail(rfqId));
            }
          },
          builder: (context, state) {
            if (state is RFQLoading) {
              return const Center(child: CircularProgressIndicator());
            }
            if (state is RFQError) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(state.message),
                    const SizedBox(height: 12),
                    ElevatedButton(
                      onPressed: () =>
                          context.read<RFQBloc>().add(LoadRFQDetail(rfqId)),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              );
            }
            if (state is! RFQDetailLoaded) return const SizedBox();
            final rfq = state.rfq;
            final myBid = rfq.bids.isNotEmpty ? rfq.bids.first : null;
            final isOpen = rfq.status == 'OPEN';
            final isAwarded = rfq.status == 'AWARDED';

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
                              Expanded(
                                child: Text(
                                  rfq.title,
                                  style: const TextStyle(
                                    fontSize: 20,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              StatusBadge(status: rfq.status),
                            ],
                          ),
                          const Divider(height: 24),
                          _row('RFQ #', rfq.rfqNumber),
                          if (rfq.deadline != null)
                            _row('Deadline', formatDate(rfq.deadline)),
                          if (rfq.budgetCents != null)
                            _row(
                              'Budget',
                              formatCurrency(rfq.budgetCents!, currency: 'INR'),
                            ),
                          if (rfq.description != null &&
                              rfq.description!.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            Text(
                              'Description',
                              style: TextStyle(
                                fontSize: 12,
                                color: AppColors.textMuted,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(rfq.description!),
                          ],
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ── Line Items ──
                  if (rfq.lineItems.isNotEmpty) ...[
                    Text(
                      'Line Items',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Card(
                      child: Column(
                        children: rfq.lineItems.asMap().entries.map((entry) {
                          final i = entry.key;
                          final item = entry.value;
                          return Column(
                            children: [
                              Padding(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 12,
                                ),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      width: 24,
                                      height: 24,
                                      decoration: BoxDecoration(
                                        color: AppColors.primary.withValues(
                                          alpha: 0.15,
                                        ),
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: Center(
                                        child: Text(
                                          '${i + 1}',
                                          style: TextStyle(
                                            fontSize: 12,
                                            fontWeight: FontWeight.bold,
                                            color: AppColors.primary,
                                          ),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            item.description,
                                            style: const TextStyle(
                                              fontWeight: FontWeight.w500,
                                            ),
                                          ),
                                          Text(
                                            'Qty: ${item.quantity.toStringAsFixed(item.quantity.truncateToDouble() == item.quantity ? 0 : 2)} ${item.unit ?? ''}',
                                            style: TextStyle(
                                              color: AppColors.textSecondary,
                                              fontSize: 13,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              if (i < rfq.lineItems.length - 1)
                                const Divider(height: 1),
                            ],
                          );
                        }).toList(),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // ── Your Submitted Bid ──
                  if (myBid != null) ...[
                    Text(
                      'Your Submitted Bid',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Card(
                      color: isAwarded
                          ? AppColors.success.withValues(alpha: 0.08)
                          : null,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (isAwarded)
                              Row(
                                children: [
                                  Icon(
                                    Icons.emoji_events,
                                    color: AppColors.success,
                                    size: 20,
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    'Bid Awarded',
                                    style: TextStyle(
                                      color: AppColors.success,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ],
                              ),
                            if (isAwarded) const SizedBox(height: 12),
                            _row(
                              'Bid Amount',
                              formatCurrency(
                                myBid.totalCents,
                                currency: 'INR',
                              ),
                            ),
                            if (myBid.deliveryDays != null)
                              _row(
                                'Lead Time',
                                '${myBid.deliveryDays} days',
                              ),
                            if (myBid.notes != null && myBid.notes!.isNotEmpty)
                              _row('Notes', myBid.notes!),
                            if (isAwarded && rfq.awardedPoId != null) ...[
                              const SizedBox(height: 12),
                              SizedBox(
                                width: double.infinity,
                                child: ElevatedButton.icon(
                                  onPressed: () => context.push(
                                    '/purchase-orders/${rfq.awardedPoId}',
                                  ),
                                  icon: const Icon(Icons.shopping_cart),
                                  label: const Text('View Awarded PO'),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppColors.success,
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // ── Bid action ──
                  if (isOpen && myBid == null)
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: () => context.push('/rfqs/$rfqId/bid'),
                        icon: const Icon(Icons.gavel),
                        label: const Text('Submit Bid'),
                        style: ElevatedButton.styleFrom(
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

  Widget _row(String label, String? value) {
    if (value == null || value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: TextStyle(
                color: AppColors.textMuted,
                fontSize: 13,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
