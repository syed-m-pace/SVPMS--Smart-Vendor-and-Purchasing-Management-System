import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../bloc/invoice_bloc.dart';

class InvoiceUploadScreen extends StatefulWidget {
  const InvoiceUploadScreen({super.key});

  @override
  State<InvoiceUploadScreen> createState() => _InvoiceUploadScreenState();
}

class _InvoiceUploadScreenState extends State<InvoiceUploadScreen> {
  final _formKey = GlobalKey<FormState>();
  final _poIdCtrl = TextEditingController();
  final _numberCtrl = TextEditingController();
  final _amountCtrl = TextEditingController();
  DateTime? _date;

  @override
  void dispose() {
    _poIdCtrl.dispose();
    _numberCtrl.dispose();
    _amountCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Upload Invoice')),
      body: BlocListener<InvoiceBloc, InvoiceState>(
        listener: (context, state) {
          if (state is InvoiceUploaded) {
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
                TextFormField(
                  controller: _poIdCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Purchase Order ID',
                    prefixIcon: Icon(Icons.shopping_cart),
                  ),
                  validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _numberCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Invoice Number',
                    prefixIcon: Icon(Icons.receipt),
                  ),
                  validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
                ),
                const SizedBox(height: 16),
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
                TextFormField(
                  controller: _amountCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Total Amount (₹)',
                    prefixIcon: Icon(Icons.currency_rupee),
                  ),
                  validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
                ),
                const SizedBox(height: 32),
                BlocBuilder<InvoiceBloc, InvoiceState>(
                  builder: (context, state) {
                    final loading = state is InvoiceLoading;
                    return ElevatedButton.icon(
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
    final amount = double.tryParse(_amountCtrl.text) ?? 0;
    context.read<InvoiceBloc>().add(
      UploadInvoice(
        poId: _poIdCtrl.text.trim(),
        invoiceNumber: _numberCtrl.text.trim(),
        invoiceDate:
            '${_date!.year}-${_date!.month.toString().padLeft(2, '0')}-${_date!.day.toString().padLeft(2, '0')}',
        totalCents: (amount * 100).toInt(),
      ),
    );
  }
}
