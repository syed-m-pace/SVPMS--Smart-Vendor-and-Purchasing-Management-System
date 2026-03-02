import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/currency_formatter.dart';
import '../../widgets/status_badge.dart';
import '../bloc/contract_bloc.dart';

class ContractListScreen extends StatefulWidget {
  const ContractListScreen({super.key});

  @override
  State<ContractListScreen> createState() => _ContractListScreenState();
}

class _ContractListScreenState extends State<ContractListScreen> {
  String _statusFilter = 'ALL';
  static const _statuses = ['ALL', 'ACTIVE', 'DRAFT', 'EXPIRED', 'TERMINATED'];
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      context.read<ContractBloc>().add(LoadMoreContracts());
    }
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<ContractBloc, ContractState>(
      builder: (context, state) {
        if (state is ContractLoading) {
          return const Center(child: CircularProgressIndicator());
        }

        if (state is ContractError) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(state.message),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () =>
                      context.read<ContractBloc>().add(LoadContracts()),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        if (state is ContractListLoaded) {
          final filtered = _statusFilter == 'ALL'
              ? state.contracts
              : state.contracts
                  .where((c) => c.status.toUpperCase() == _statusFilter)
                  .toList();

          return Column(
            children: [
              // Status filter chips
              SizedBox(
                height: 48,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  children: _statuses.map((s) {
                    final selected = _statusFilter == s;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: FilterChip(
                        label: Text(s),
                        selected: selected,
                        onSelected: (_) =>
                            setState(() => _statusFilter = s),
                        selectedColor:
                            AppColors.primary.withValues(alpha: 0.15),
                        checkmarkColor: AppColors.primary,
                        labelStyle: TextStyle(
                          fontSize: 12,
                          color: selected
                              ? AppColors.primary
                              : AppColors.textSecondary,
                          fontWeight:
                              selected ? FontWeight.w600 : FontWeight.normal,
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
                              Icons.description_outlined,
                              size: 64,
                              color: AppColors.textMuted,
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'No contracts found',
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
                            context.read<ContractBloc>().add(RefreshContracts()),
                        child: ListView.builder(
                          controller: _scrollController,
                          padding: const EdgeInsets.all(16),
                          itemCount: filtered.length + (state.hasMore && _statusFilter == 'ALL' ? 1 : 0),
                          itemBuilder: (context, index) {
                            if (index >= filtered.length) {
                              return const Padding(
                                padding: EdgeInsets.all(16),
                                child: Center(child: CircularProgressIndicator()),
                              );
                            }
                            final contract = filtered[index];
                            return Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                onTap: () => context
                                    .push('/contracts/${contract.id}'),
                                title: Text(
                                  contract.title,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w600),
                                ),
                                subtitle: Text(
                                  '${contract.contractNumber} • ${contract.valueCents != null ? formatCurrency(contract.valueCents!) : "—"}',
                                  style: TextStyle(
                                      color: AppColors.textSecondary),
                                ),
                                trailing:
                                    StatusBadge(status: contract.status),
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
