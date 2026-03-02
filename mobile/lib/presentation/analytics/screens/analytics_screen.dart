import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/datasources/api/api_client.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  late Future<Map<String, dynamic>> _scorecardFuture;

  @override
  void initState() {
    super.initState();
    _scorecardFuture = _fetchScorecard();
  }

  Future<Map<String, dynamic>> _fetchScorecard() async {
    final client = context.read<ApiClient>();
    // Get vendor profile first to get vendor_id
    final vendor = await client.getVendorMe();
    final vendorId = vendor['id'] as String;
    return client.getVendorScorecard(vendorId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Performance Analytics')),
      body: RefreshIndicator(
        onRefresh: () async {
          setState(() {
            _scorecardFuture = _fetchScorecard();
          });
          await _scorecardFuture;
        },
        child: FutureBuilder<Map<String, dynamic>>(
          future: _scorecardFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.analytics_outlined,
                        size: 64, color: AppColors.textMuted),
                    const SizedBox(height: 12),
                    Text(
                      'Failed to load analytics',
                      style: TextStyle(
                          fontSize: 16, color: AppColors.textSecondary),
                    ),
                    const SizedBox(height: 12),
                    ElevatedButton(
                      onPressed: () => setState(() {
                        _scorecardFuture = _fetchScorecard();
                      }),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              );
            }

            final data = snapshot.data!;
            final compositeScore = (data['composite_score'] as num?)?.toDouble();

            return SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Overall Score ──
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        children: [
                          Text(
                            'Overall Score',
                            style: GoogleFonts.inter(
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textSecondary,
                            ),
                          ),
                          const SizedBox(height: 16),
                          SizedBox(
                            width: 120,
                            height: 120,
                            child: Stack(
                              fit: StackFit.expand,
                              children: [
                                CircularProgressIndicator(
                                  value: compositeScore != null
                                      ? compositeScore / 100
                                      : 0,
                                  strokeWidth: 10,
                                  backgroundColor: AppColors.border,
                                  color: _scoreColor(compositeScore),
                                ),
                                Center(
                                  child: Text(
                                    compositeScore != null
                                        ? '${compositeScore.toStringAsFixed(0)}%'
                                        : 'N/A',
                                    style: GoogleFonts.inter(
                                      fontSize: 28,
                                      fontWeight: FontWeight.w800,
                                      color: _scoreColor(compositeScore),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            _scoreLabel(compositeScore),
                            style: GoogleFonts.inter(
                              fontSize: 14,
                              color: _scoreColor(compositeScore),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ── KPI Cards ──
                  Text(
                    'Key Performance Indicators',
                    style: GoogleFonts.inter(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 12),
                  _kpiCard(
                    icon: Icons.local_shipping_outlined,
                    label: 'On-Time Delivery',
                    value: data['on_time_delivery_rate'],
                    suffix: '%',
                  ),
                  _kpiCard(
                    icon: Icons.receipt_long_outlined,
                    label: 'Invoice Acceptance',
                    value: data['invoice_acceptance_rate'],
                    suffix: '%',
                  ),
                  _kpiCard(
                    icon: Icons.check_circle_outline,
                    label: 'PO Fulfillment',
                    value: data['po_fulfillment_rate'],
                    suffix: '%',
                  ),
                  _kpiCard(
                    icon: Icons.question_answer_outlined,
                    label: 'RFQ Response Rate',
                    value: data['rfq_response_rate'],
                    suffix: '%',
                  ),
                  _kpiCard(
                    icon: Icons.timer_outlined,
                    label: 'Avg Invoice Processing',
                    value: data['avg_invoice_processing_days'],
                    suffix: ' days',
                  ),
                  const SizedBox(height: 16),

                  // ── Volume Metrics ──
                  Text(
                    'Volume Metrics',
                    style: GoogleFonts.inter(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      _volumeChip(
                        label: 'Total POs',
                        value: '${data['total_pos'] ?? 0}',
                        icon: Icons.shopping_cart_outlined,
                      ),
                      const SizedBox(width: 8),
                      _volumeChip(
                        label: 'Invoices',
                        value: '${data['total_invoices'] ?? 0}',
                        icon: Icons.receipt_outlined,
                      ),
                      const SizedBox(width: 8),
                      _volumeChip(
                        label: 'RFQs',
                        value: '${data['total_rfqs_invited'] ?? 0}',
                        icon: Icons.request_quote_outlined,
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _kpiCard({
    required IconData icon,
    required String label,
    required dynamic value,
    required String suffix,
  }) {
    final numValue = value != null ? (value as num).toDouble() : null;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AppColors.primary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: AppColors.primary, size: 24),
        ),
        title: Text(label),
        trailing: Text(
          numValue != null
              ? '${numValue.toStringAsFixed(1)}$suffix'
              : 'N/A',
          style: GoogleFonts.inter(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: numValue != null
                ? _scoreColor(numValue)
                : AppColors.textMuted,
          ),
        ),
      ),
    );
  }

  Widget _volumeChip({
    required String label,
    required String value,
    required IconData icon,
  }) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            children: [
              Icon(icon, color: AppColors.primary, size: 24),
              const SizedBox(height: 8),
              Text(
                value,
                style: GoogleFonts.inter(
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _scoreColor(double? score) {
    if (score == null) return AppColors.textMuted;
    if (score >= 80) return AppColors.success;
    if (score >= 60) return Colors.orange;
    return AppColors.destructive;
  }

  String _scoreLabel(double? score) {
    if (score == null) return 'Insufficient Data';
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Needs Improvement';
    return 'Critical';
  }
}
