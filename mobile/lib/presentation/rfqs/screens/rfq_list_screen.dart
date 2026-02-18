import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/date_formatter.dart';
import '../../widgets/status_badge.dart';
import '../bloc/rfq_bloc.dart';

class RFQListScreen extends StatelessWidget {
  const RFQListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<RFQBloc, RFQState>(
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
                  onPressed: () => context.read<RFQBloc>().add(LoadRFQs()),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }
        if (state is RFQListLoaded) {
          if (state.rfqs.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.gavel_outlined,
                    size: 64,
                    color: AppColors.textMuted,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'No RFQs available',
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
            onRefresh: () async => context.read<RFQBloc>().add(LoadRFQs()),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: state.rfqs.length,
              itemBuilder: (context, i) {
                final rfq = state.rfqs[i];
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    title: Text(
                      rfq.title,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(
                      '${rfq.rfqNumber} • Deadline: ${formatDate(rfq.deadline)}',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                    trailing: StatusBadge(status: rfq.status),
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
