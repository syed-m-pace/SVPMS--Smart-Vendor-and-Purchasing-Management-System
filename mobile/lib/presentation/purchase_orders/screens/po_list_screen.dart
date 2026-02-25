import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/currency_formatter.dart';
import '../../widgets/status_badge.dart';
import '../bloc/po_bloc.dart';

class POListScreen extends StatefulWidget {
  const POListScreen({super.key});

  @override
  State<POListScreen> createState() => _POListScreenState();
}

class _POListScreenState extends State<POListScreen> {
  String _statusFilter = 'ALL';
  static const _statuses = ['ALL', 'ISSUED', 'ACKNOWLEDGED', 'FULFILLED', 'CLOSED'];

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<POBloc, POState>(
      builder: (context, state) {
        if (state is POLoading) {
          return const Center(child: CircularProgressIndicator());
        }

        if (state is POError) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(state.message),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => context.read<POBloc>().add(LoadPOs()),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        if (state is POListLoaded) {
          final filtered = _statusFilter == 'ALL'
              ? state.orders
              : state.orders
                  .where((po) => po.status.toUpperCase() == _statusFilter)
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
                              Icons.shopping_cart_outlined,
                              size: 64,
                              color: AppColors.textMuted,
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'No purchase orders',
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
                            context.read<POBloc>().add(LoadPOs()),
                        child: ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: filtered.length,
                          itemBuilder: (context, index) {
                            final po = filtered[index];
                            return Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                onTap: () =>
                                    context.push('/purchase-orders/${po.id}'),
                                title: Text(
                                  po.poNumber,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w600),
                                ),
                                subtitle: Text(
                                  '${formatCurrency(po.totalCents)} • ${po.vendorName ?? ""}',
                                  style:
                                      TextStyle(color: AppColors.textSecondary),
                                ),
                                trailing: StatusBadge(status: po.status),
                              ),
                            );
                          },
                        ),
                      ),
              ),
            ],
          );
        }

        return const SizedBox();
      },
    );
  }
}
