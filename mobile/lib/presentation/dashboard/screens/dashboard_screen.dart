import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/purchase_order.dart';
import '../../../core/utils/currency_formatter.dart';
import '../../widgets/stat_card.dart';
import '../../widgets/status_badge.dart';
import '../bloc/dashboard_bloc.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<DashboardBloc, DashboardState>(
      builder: (context, state) {
        if (state is DashboardLoading) {
          return const Center(child: CircularProgressIndicator());
        }

        if (state is DashboardError) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.error_outline,
                  size: 48,
                  color: AppColors.destructive,
                ),
                const SizedBox(height: 12),
                Text(state.message, textAlign: TextAlign.center),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () =>
                      context.read<DashboardBloc>().add(LoadDashboard()),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        if (state is DashboardLoaded) {
          return RefreshIndicator(
            onRefresh: () async {
              context.read<DashboardBloc>().add(RefreshDashboard());
            },
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // ── Stat cards ──
                GridView.count(
                  crossAxisCount: 2,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  children: [
                    StatCard(
                      title: 'Active POs',
                      value: state.stats.activePOs.toString(),
                      icon: Icons.shopping_cart,
                      color: AppColors.success,
                      onTap: () => context.go('/purchase-orders'),
                    ),
                    StatCard(
                      title: 'Pending RFQs',
                      value: state.stats.pendingRFQs.toString(),
                      icon: Icons.attach_money,
                      color: AppColors.accent,
                      onTap: () => context.go('/rfqs'),
                    ),
                    StatCard(
                      title: 'Open Invoices',
                      value: state.stats.openInvoices.toString(),
                      icon: Icons.receipt_long,
                      color: AppColors.info,
                      onTap: () => context.go('/invoices'),
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                // ── Recent POs ──
                Text(
                  'Recent Purchase Orders',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 12),
                if (state.recentPOs.isEmpty)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Center(
                        child: Text(
                          'No purchase orders yet',
                          style: TextStyle(color: AppColors.textMuted),
                        ),
                      ),
                    ),
                  )
                else
                  ...state.recentPOs.map((po) => _POCard(po: po)),
              ],
            ),
          );
        }

        return const SizedBox();
      },
    );
  }
}

class _POCard extends StatelessWidget {
  final PurchaseOrder po;
  const _POCard({required this.po});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        onTap: () => context.push('/purchase-orders/${po.id}'),
        title: Text(
          po.poNumber,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Text(formatCurrency(po.totalCents)),
        trailing: StatusBadge(status: po.status),
      ),
    );
  }
}
