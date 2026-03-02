import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/currency_formatter.dart';
import '../../../core/utils/date_formatter.dart';
import '../../../data/repositories/contract_repository.dart';
import '../../widgets/status_badge.dart';
import '../bloc/contract_bloc.dart';

class ContractDetailScreen extends StatelessWidget {
  final String contractId;
  const ContractDetailScreen({super.key, required this.contractId});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) => ContractBloc(
        repo: context.read<ContractRepository>(),
      )..add(LoadContractDetail(contractId)),
      child: Scaffold(
        appBar: AppBar(title: const Text('Contract')),
        body: BlocBuilder<ContractBloc, ContractState>(
          builder: (context, state) {
            if (state is ContractLoading) {
              return const Center(child: CircularProgressIndicator());
            }
            if (state is ContractError) {
              return Center(child: Text(state.message));
            }

            final contract =
                state is ContractDetailLoaded ? state.contract : null;
            if (contract == null) return const SizedBox();

            return RefreshIndicator(
              onRefresh: () async {
                context
                    .read<ContractBloc>()
                    .add(LoadContractDetail(contractId));
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
                              mainAxisAlignment:
                                  MainAxisAlignment.spaceBetween,
                              children: [
                                Expanded(
                                  child: Text(
                                    contract.title,
                                    style: const TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                StatusBadge(status: contract.status),
                              ],
                            ),
                            const Divider(height: 24),
                            _row('Contract #', contract.contractNumber),
                            if (contract.vendorName != null)
                              _row('Vendor', contract.vendorName!),
                            _row(
                              'Value',
                              contract.valueCents != null
                                  ? formatCurrency(contract.valueCents!)
                                  : '—',
                            ),
                            _row('Currency', contract.currency),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // ── Dates card ──
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Dates & Renewal',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            _row('Start Date',
                                formatDate(contract.startDate)),
                            _row(
                                'End Date', formatDate(contract.endDate)),
                            _row('Auto Renew',
                                contract.autoRenew ? 'Yes' : 'No'),
                            _row('Renewal Notice',
                                '${contract.renewalNoticeDays} days'),
                            if (contract.terminatedAt != null)
                              _row('Terminated',
                                  formatDate(contract.terminatedAt!)),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // ── Description ──
                    if (contract.description != null &&
                        contract.description!.isNotEmpty)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Description',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                contract.description!,
                                style: TextStyle(
                                  color: AppColors.textSecondary,
                                  height: 1.5,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),

                    // ── SLA Terms ──
                    if (contract.slaTerms != null &&
                        contract.slaTerms!.isNotEmpty) ...[
                      const SizedBox(height: 16),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'SLA Terms',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                contract.slaTerms!,
                                style: TextStyle(
                                  color: AppColors.textSecondary,
                                  height: 1.5,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],

                    // ── Terminated banner ──
                    if (contract.status == 'TERMINATED') ...[
                      const SizedBox(height: 16),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color:
                              AppColors.destructive.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: AppColors.destructive
                                .withValues(alpha: 0.3),
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.cancel_outlined,
                                color: AppColors.destructive),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                'This contract has been terminated',
                                style: TextStyle(
                                  color: AppColors.destructive,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
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
}
