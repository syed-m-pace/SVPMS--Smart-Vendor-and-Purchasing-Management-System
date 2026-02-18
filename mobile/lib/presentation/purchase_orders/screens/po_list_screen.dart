import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/currency_formatter.dart';
import '../../widgets/status_badge.dart';
import '../bloc/po_bloc.dart';

class POListScreen extends StatelessWidget {
  const POListScreen({super.key});

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
          if (state.orders.isEmpty) {
            return Center(
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
            );
          }

          return RefreshIndicator(
            onRefresh: () async => context.read<POBloc>().add(LoadPOs()),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: state.orders.length,
              itemBuilder: (context, index) {
                final po = state.orders[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    onTap: () => context.push('/purchase-orders/${po.id}'),
                    title: Text(
                      po.poNumber,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(
                      '${formatCurrency(po.totalCents)} • ${po.vendorName ?? ""}',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                    trailing: StatusBadge(status: po.status),
                  ),
                );
              },
            ),
          );
        }

        return const SizedBox();
      },
    );
  }
}
