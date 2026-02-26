import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:file_picker/file_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/currency_formatter.dart';
import '../../../core/utils/date_formatter.dart';
import '../../../data/models/invoice.dart';
import '../../../data/repositories/invoice_repository.dart';
import '../../widgets/status_badge.dart';
import '../bloc/invoice_bloc.dart';

class InvoiceDetailScreen extends StatefulWidget {
  final String invoiceId;

  const InvoiceDetailScreen({super.key, required this.invoiceId});

  @override
  State<InvoiceDetailScreen> createState() => _InvoiceDetailScreenState();
}

class _InvoiceDetailScreenState extends State<InvoiceDetailScreen> {
  Invoice? _invoice;
  bool _loading = true;
  String? _error;
  bool _openingDoc = false;
  bool _uploading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final repo = context.read<InvoiceRepository>();
      final invoice = await repo.get(widget.invoiceId);
      if (mounted) {
        setState(() {
          _invoice = invoice;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  void _showDisputeDialog(BuildContext context, String invoiceId) {
    final reasonController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Dispute Invoice'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Provide a reason for disputing this invoice (optional):',
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: reasonController,
              maxLines: 3,
              decoration: const InputDecoration(
                hintText: 'e.g. Amount does not match agreed price',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              context.read<InvoiceBloc>().add(
                DisputeInvoice(
                  invoiceId: invoiceId,
                  reason: reasonController.text.trim().isEmpty
                      ? null
                      : reasonController.text.trim(),
                ),
              );
            },
            child: const Text('Dispute'),
          ),
        ],
      ),
    );
  }

  Future<void> _openDocument() async {
    final docUrl = _invoice?.documentUrl;
    if (docUrl == null) return;
    setState(() => _openingDoc = true);
    try {
      final repo = context.read<InvoiceRepository>();
      final presignedUrl = await repo.getPresignedUrl(docUrl);
      final uri = Uri.parse(presignedUrl);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not open document')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to open document: $e')));
      }
    } finally {
      if (mounted) setState(() => _openingDoc = false);
    }
  }

  Future<void> _pickAndReupload() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'png', 'jpg', 'jpeg'],
      );
      if (result == null || result.files.single.path == null) return;

      setState(() => _uploading = true);
      if (!mounted) return;
      context.read<InvoiceBloc>().add(
        ReuploadInvoice(
          invoiceId: widget.invoiceId,
          filePath: result.files.single.path!,
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to pick file: $e')));
        setState(() => _uploading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return BlocListener<InvoiceBloc, InvoiceState>(
      listener: (context, state) {
        if (state is InvoiceDisputed) {
          setState(() => _invoice = state.invoice);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Invoice disputed successfully')),
          );
        } else if (state is InvoiceReuploaded) {
          setState(() {
            _invoice = state.invoice;
            _uploading = false;
          });
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Invoice re-uploaded successfully')),
          );
        } else if (state is InvoiceError) {
          setState(() => _uploading = false);
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text('Error: ${state.message}')));
        }
      },
      child: Scaffold(
        appBar: AppBar(title: const Text('Invoice')),
        body: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null && _invoice == null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(_error!, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            ElevatedButton(onPressed: _load, child: const Text('Retry')),
          ],
        ),
      );
    }

    final inv = _invoice!;

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
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          'Invoice #${inv.invoiceNumber}',
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      StatusBadge(status: inv.status),
                    ],
                  ),
                  if (inv.vendorName != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      inv.vendorName!,
                      style: TextStyle(
                        fontSize: 14,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                  const Divider(height: 24),
                  _row('PO #', inv.poNumber ?? 'N/A'),
                  _row('Invoice Date', formatDate(inv.invoiceDate)),
                  _row('Total', formatCurrency(inv.totalCents)),
                  _row('Currency', inv.currency),
                  if (inv.matchStatus != null)
                    _rowWidget(
                      'Match Status',
                      StatusBadge(status: inv.matchStatus!),
                    ),
                  if (inv.ocrStatus != null)
                    _rowWidget(
                      'OCR Status',
                      StatusBadge(status: inv.ocrStatus!),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // ── View Document button ──
          if (inv.documentUrl != null)
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _openingDoc ? null : _openDocument,
                icon: _openingDoc
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.open_in_new),
                label: Text(
                  _openingDoc ? 'Opening...' : 'View Invoice Document',
                ),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),

          // Match Exceptions section
          if (inv.matchExceptions != null &&
              inv.matchExceptions!['manual_dispute_reason'] != null) ...[
            const SizedBox(height: 16),
            _statusBanner(
              icon: Icons.info_outline,
              color: Colors.red,
              title: 'Manual Dispute Reason',
              message: inv.matchExceptions!['manual_dispute_reason'].toString(),
            ),
          ],

          // ── Status guidance ──
          if (inv.status == 'UPLOADED') ...[
            const SizedBox(height: 16),
            _statusBanner(
              icon: Icons.hourglass_top_outlined,
              color: Colors.blue,
              message:
                  'OCR processing in progress. The invoice will be automatically matched against the purchase order once extraction completes.',
            ),
          ],
          if (inv.status == 'MATCHED') ...[
            const SizedBox(height: 16),
            _statusBanner(
              icon: Icons.check_circle_outline,
              color: Colors.green,
              message:
                  '3-way match passed. This invoice is ready for payment approval.',
            ),
          ],
          if (inv.status == 'EXCEPTION' || inv.status == 'DISPUTED') ...[
            const SizedBox(height: 16),
            _statusBanner(
              icon: Icons.warning_amber_outlined,
              color: Colors.orange,
              message: inv.status == 'EXCEPTION'
                  ? 'A match exception was detected. Please review and re-upload or dispute.'
                  : 'This invoice has been disputed. Please re-upload a corrected version.',
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                icon: _uploading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.upload_file),
                label: Text(_uploading ? 'Uploading...' : 'Re-upload Invoice'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                onPressed: _uploading ? null : _pickAndReupload,
              ),
            ),
            if (inv.status == 'EXCEPTION') ...[
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.report_problem_outlined),
                  label: const Text('Dispute This Invoice'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.orange,
                    side: const BorderSide(color: Colors.orange),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  onPressed: () => _showDisputeDialog(context, inv.id),
                ),
              ),
            ],
          ],
          if (inv.status == 'PAID') ...[
            const SizedBox(height: 16),
            _statusBanner(
              icon: Icons.payments_outlined,
              color: Colors.teal,
              message: 'This invoice has been paid.',
            ),
          ],
        ],
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

  Widget _rowWidget(String label, Widget child) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: AppColors.textSecondary)),
          child,
        ],
      ),
    );
  }

  Widget _statusBanner({
    required IconData icon,
    required MaterialColor color,
    required String message,
    String? title,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.shade200),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color.shade700, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (title != null) ...[
                  Text(
                    title,
                    style: TextStyle(
                      color: color.shade900,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 4),
                ],
                Text(
                  message,
                  style: TextStyle(color: color.shade700, fontSize: 13),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
