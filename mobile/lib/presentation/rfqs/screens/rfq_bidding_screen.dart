import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/currency_formatter.dart';
import '../../../core/utils/date_formatter.dart';
import '../../widgets/status_badge.dart';
import '../bloc/rfq_bloc.dart';

class RFQBiddingScreen extends StatefulWidget {
  final String rfqId;
  const RFQBiddingScreen({super.key, required this.rfqId});

  @override
  State<RFQBiddingScreen> createState() => _RFQBiddingScreenState();
}

class _RFQBiddingScreenState extends State<RFQBiddingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _priceCtrl = TextEditingController();
  final _leadTimeCtrl = TextEditingController();
  final _commentsCtrl = TextEditingController();

  @override
  void dispose() {
    _priceCtrl.dispose();
    _leadTimeCtrl.dispose();
    _commentsCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) => RFQBloc(
        repo: context.read(), // Using read() to get from RepositoryProvider
      )..add(LoadRFQDetail(widget.rfqId)),
      child: Scaffold(
        appBar: AppBar(title: const Text('Submit Bid')),
        body: BlocConsumer<RFQBloc, RFQState>(
          listener: (context, state) {
            if (state is BidSubmitted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Bid submitted successfully'),
                  backgroundColor: AppColors.success,
                ),
              );
              context.pop();
            }
            if (state is RFQError) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(state.message),
                  backgroundColor: AppColors.destructive,
                ),
              );
            }
          },
          builder: (context, state) {
            if (state is RFQLoading) {
              return const Center(child: CircularProgressIndicator());
            }

            if (state is RFQDetailLoaded) {
              final rfq = state.rfq;
              return SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // ── RFQ Details ──
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
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                                StatusBadge(status: rfq.status),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              rfq.rfqNumber,
                              style: TextStyle(
                                color: AppColors.textMuted,
                                fontSize: 13,
                              ),
                            ),
                            const Divider(height: 24),
                            if (rfq.description != null) Text(rfq.description!),
                            const SizedBox(height: 16),
                            _row(
                              'Budget',
                              formatCurrency(rfq.budgetCents ?? 0),
                            ),
                            if (rfq.deadline != null)
                              _row('Deadline', formatDate(rfq.deadline)),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),

                    // ── Bid Form ──
                    const Text(
                      'Your Bid',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Form(
                      key: _formKey,
                      child: Column(
                        children: [
                          TextFormField(
                            controller: _priceCtrl,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(
                              labelText: 'Unit Price (₹)',
                              prefixIcon: Icon(Icons.currency_rupee),
                              helperText: 'Enter price per unit',
                            ),
                            validator: (v) {
                              if (v == null || v.isEmpty) return 'Required';
                              if (double.tryParse(v) == null) {
                                return 'Invalid number';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: _leadTimeCtrl,
                            keyboardType: TextInputType.number,
                            inputFormatters: [
                              FilteringTextInputFormatter.digitsOnly,
                            ],
                            decoration: const InputDecoration(
                              labelText: 'Lead Time (Days)',
                              prefixIcon: Icon(Icons.schedule),
                              helperText: 'Days to deliver after PO',
                            ),
                            validator: (v) =>
                                v?.isEmpty ?? true ? 'Required' : null,
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: _commentsCtrl,
                            maxLines: 3,
                            decoration: const InputDecoration(
                              labelText: 'Comments (Optional)',
                              prefixIcon: Icon(Icons.comment),
                              alignLabelWithHint: true,
                            ),
                          ),
                          const SizedBox(height: 32),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: () {
                                if (_formKey.currentState!.validate()) {
                                  final price =
                                      double.tryParse(_priceCtrl.text) ?? 0;
                                  final leadTime =
                                      int.tryParse(_leadTimeCtrl.text) ?? 0;
                                  context.read<RFQBloc>().add(
                                    SubmitBid(
                                      rfqId: rfq.id,
                                      unitPriceCents: (price * 100).toInt(),
                                      leadTimeDays: leadTime,
                                      comments: _commentsCtrl.text,
                                    ),
                                  );
                                }
                              },
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(
                                  vertical: 16,
                                ),
                              ),
                              child: const Text('Submit Bid'),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }

            return const Center(child: Text('Something went wrong'));
          },
        ),
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
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
