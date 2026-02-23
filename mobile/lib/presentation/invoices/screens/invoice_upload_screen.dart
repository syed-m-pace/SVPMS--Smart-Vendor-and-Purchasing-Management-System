import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../purchase_orders/bloc/po_bloc.dart';
import '../bloc/invoice_bloc.dart';

class InvoiceUploadScreen extends StatefulWidget {
  const InvoiceUploadScreen({super.key});

  @override
  State<InvoiceUploadScreen> createState() => _InvoiceUploadScreenState();
}

class _InvoiceUploadScreenState extends State<InvoiceUploadScreen> {
  final _formKey = GlobalKey<FormState>();
  String? _selectedPoId;
  final _numberCtrl = TextEditingController();
  final _amountCtrl = TextEditingController();
  DateTime? _date;
  PlatformFile? _selectedFile;

  @override
  void dispose() {
    _numberCtrl.dispose();
    _amountCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'jpg', 'jpeg', 'png'],
    );
    if (result != null) {
      setState(() => _selectedFile = result.files.first);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Upload Invoice')),
      body: BlocListener<InvoiceBloc, InvoiceState>(
        listener: (context, state) {
          if (state is InvoiceUploaded) {
            context.read<InvoiceBloc>().add(LoadInvoices());
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Invoice uploaded successfully'),
                backgroundColor: AppColors.success,
              ),
            );
            context.pop();
          }
          if (state is InvoiceError) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(state.message),
                backgroundColor: AppColors.destructive,
              ),
            );
          }
        },
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // ── PO Dropdown ──
                BlocBuilder<POBloc, POState>(
                  builder: (context, state) {
                    List<DropdownMenuItem<String>> items = [];
                    if (state is POListLoaded) {
                      items = state.orders
                          .map(
                            (po) => DropdownMenuItem(
                              value: po.id,
                              child: Text(
                                '${po.poNumber} (${po.status})',
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          )
                          .toList();
                    }

                    return DropdownButtonFormField<String>(
                      key: const Key('invoice_po_dropdown'),
                      initialValue: _selectedPoId,
                      items: items,
                      onChanged: (val) => setState(() => _selectedPoId = val),
                      decoration: const InputDecoration(
                        labelText: 'Purchase Order',
                        prefixIcon: Icon(Icons.shopping_cart),
                        helperText: 'Select the PO for this invoice *',
                      ),
                      validator: (v) => v == null ? 'Required' : null,
                    );
                  },
                ),
                const SizedBox(height: 16),

                // ── Invoice Number ──
                TextFormField(
                  key: const Key('invoice_number_input'),
                  controller: _numberCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Invoice Number',
                    prefixIcon: Icon(Icons.receipt),
                  ),
                  validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
                ),
                const SizedBox(height: 16),

                // ── Date Picker ──
                TextFormField(
                  readOnly: true,
                  decoration: InputDecoration(
                    labelText: 'Invoice Date',
                    prefixIcon: const Icon(Icons.calendar_today),
                    hintText: _date != null
                        ? '${_date!.day}/${_date!.month}/${_date!.year}'
                        : 'Select date',
                  ),
                  controller: TextEditingController(
                    text: _date != null
                        ? '${_date!.day}/${_date!.month}/${_date!.year}'
                        : '',
                  ),
                  onTap: () async {
                    final d = await showDatePicker(
                      context: context,
                      initialDate: DateTime.now(),
                      firstDate: DateTime(2020),
                      lastDate: DateTime.now(),
                    );
                    if (d != null) setState(() => _date = d);
                  },
                  validator: (_) => _date == null ? 'Required' : null,
                ),
                const SizedBox(height: 16),

                // ── Amount ──
                TextFormField(
                  key: const Key('invoice_amount_input'),
                  controller: _amountCtrl,
                  keyboardType: TextInputType.number,
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
                  ],
                  decoration: const InputDecoration(
                    labelText: 'Total Amount (₹)',
                    prefixIcon: Icon(Icons.currency_rupee),
                  ),
                  validator: (v) {
                    if (v == null || v.isEmpty) return 'Required';
                    if (double.tryParse(v) == null) return 'Invalid amount';
                    return null;
                  },
                ),
                const SizedBox(height: 16),

                // ── File Selection ──
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.grey.shade300),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Invoice Document',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: Colors.grey,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              _selectedFile?.name ?? 'No file selected',
                              style: TextStyle(
                                color: _selectedFile != null
                                    ? Colors.black87
                                    : Colors.grey,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          TextButton.icon(
                            onPressed: _pickFile,
                            icon: const Icon(Icons.attach_file),
                            label: const Text('Select'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                if (_selectedFile == null)
                  const Padding(
                    padding: EdgeInsets.only(top: 4, left: 12),
                    child: Text(
                      'Required *',
                      style: TextStyle(
                        color: AppColors.destructive,
                        fontSize: 12,
                      ),
                    ),
                  ),

                const SizedBox(height: 32),

                // ── Submit Button ──
                BlocBuilder<InvoiceBloc, InvoiceState>(
                  builder: (context, state) {
                    final loading = state is InvoiceLoading;
                    return ElevatedButton.icon(
                      key: const Key('invoice_submit_button'),
                      onPressed: loading ? null : _submit,
                      icon: loading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Icon(Icons.upload),
                      label: const Text('Upload Invoice'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedFile == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please select a document'),
          backgroundColor: AppColors.destructive,
        ),
      );
      return;
    }

    final amount = double.tryParse(_amountCtrl.text) ?? 0;
    context.read<InvoiceBloc>().add(
      UploadInvoice(
        poId: _selectedPoId!,
        invoiceNumber: _numberCtrl.text.trim(),
        invoiceDate:
            '${_date!.year}-${_date!.month.toString().padLeft(2, '0')}-${_date!.day.toString().padLeft(2, '0')}',
        totalCents: (amount * 100).toInt(),
        filePath: _selectedFile!.path,
      ),
    );
  }
}
