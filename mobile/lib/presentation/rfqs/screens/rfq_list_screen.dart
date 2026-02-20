import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/date_formatter.dart';
import '../../widgets/status_badge.dart';
import '../bloc/rfq_bloc.dart';

class RFQListScreen extends StatefulWidget {
  const RFQListScreen({super.key});

  @override
  State<RFQListScreen> createState() => _RFQListScreenState();
}

class _RFQListScreenState extends State<RFQListScreen> {
  String? _selectedStatus;

  static const _statuses = ['DRAFT', 'OPEN', 'CLOSED', 'AWARDED'];

  void _applyFilter(String? status) {
    setState(() => _selectedStatus = status);
    context.read<RFQBloc>().add(LoadRFQs(status: status));
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // ── Status filter bar ──
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              _filterChip(null, 'All'),
              ..._statuses.map((s) => _filterChip(s, s)),
            ],
          ),
        ),

        // ── Content ──
        Expanded(
          child: BlocBuilder<RFQBloc, RFQState>(
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
                        onPressed: () => context.read<RFQBloc>().add(
                          LoadRFQs(status: _selectedStatus),
                        ),
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
                  onRefresh: () async =>
                      context.read<RFQBloc>().add(RefreshRFQs()),
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    itemCount: state.rfqs.length,
                    itemBuilder: (context, i) {
                      final rfq = state.rfqs[i];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          onTap: () => context.push('/rfqs/${rfq.id}/bid'),
                          title: Text(
                            rfq.title,
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                rfq.rfqNumber,
                                style: TextStyle(
                                  color: AppColors.textMuted,
                                  fontSize: 12,
                                ),
                              ),
                              if (rfq.deadline != null)
                                Text(
                                  'Deadline: ${formatDate(rfq.deadline)}',
                                  style: TextStyle(
                                    color: AppColors.textSecondary,
                                    fontSize: 13,
                                  ),
                                ),
                              if (rfq.bids.isNotEmpty)
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 6,
                                    vertical: 2,
                                  ),
                                  margin: const EdgeInsets.only(top: 4),
                                  decoration: BoxDecoration(
                                    color: AppColors.success.withValues(
                                      alpha: 0.1,
                                    ),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: const Text(
                                    'Bid Submitted',
                                    style: TextStyle(
                                      color: AppColors.success,
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                          trailing: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [StatusBadge(status: rfq.status)],
                          ),
                          isThreeLine: rfq.deadline != null,
                        ),
                      );
                    },
                  ),
                );
              }
              return const SizedBox();
            },
          ),
        ),
      ],
    );
  }

  Widget _filterChip(String? value, String label) {
    final selected = _selectedStatus == value;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: FilterChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => _applyFilter(value),
        selectedColor: AppColors.primary.withValues(alpha: 0.2),
        checkmarkColor: AppColors.primary,
      ),
    );
  }
}
