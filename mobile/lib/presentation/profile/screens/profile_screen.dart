import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/datasources/api/api_client.dart';
import '../../../data/models/vendor.dart';
import '../../auth/bloc/auth_bloc.dart';
import '../../widgets/status_badge.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late Future<Vendor> _vendorFuture;

  @override
  void initState() {
    super.initState();
    _vendorFuture = _fetchVendor();
  }

  Future<Vendor> _fetchVendor() async {
    final client = context.read<ApiClient>();
    final data = await client.getMe();
    return Vendor.fromJson(data);
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<AuthBloc, AuthState>(
      listener: (context, state) {
        // If logged out, GoRouter redirect will handle navigation
      },
      builder: (context, state) {
        return Scaffold(
          body: RefreshIndicator(
            onRefresh: () async {
              setState(() {
                _vendorFuture = _fetchVendor();
              });
              await _vendorFuture;
            },
            child: FutureBuilder<Vendor>(
              future: _vendorFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text('Failed to load profile'),
                        TextButton(
                          onPressed: () => setState(() {
                            _vendorFuture = _fetchVendor();
                          }),
                          child: const Text('Retry'),
                        ),
                        const SizedBox(height: 24),
                        // Fallback logout
                        _logoutButton(context),
                      ],
                    ),
                  );
                }

                final vendor = snapshot.data;
                // Use Auth user as fallback/supplement if needed, but vendor data is primary
                final user = state is Authenticated ? state.user : null;

                return ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    const SizedBox(height: 20),
                    // ── Avatar ──
                    Center(
                      child: Container(
                        width: 96,
                        height: 96,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [AppColors.primary, AppColors.accent],
                          ),
                          borderRadius: BorderRadius.circular(24),
                        ),
                        child: Center(
                          child: Text(
                            vendor?.legalName
                                    .split(' ')
                                    .map((w) => w.isNotEmpty ? w[0] : '')
                                    .take(2)
                                    .join()
                                    .toUpperCase() ??
                                '?',
                            style: GoogleFonts.inter(
                              fontSize: 32,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Center(
                      child: Text(
                        vendor?.legalName ?? 'Unknown Vendor',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    if (vendor?.status != null)
                      Center(child: StatusBadge(status: vendor!.status)),
                    const SizedBox(height: 8),
                    Center(
                      child: Text(
                        user?.email ?? vendor?.email ?? '',
                        style: TextStyle(
                          fontSize: 13,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),

                    // ── Vendor Details ──
                    Card(
                      child: Column(
                        children: [
                          _tile(
                            Icons.person_outline,
                            'Contact Person',
                            subtitle: vendor?.contactPerson ?? 'N/A',
                          ),
                          const Divider(height: 1),
                          _tile(
                            Icons.receipt_long,
                            'GST Number',
                            subtitle: vendor?.gstNumber ?? 'N/A',
                          ),
                          const Divider(height: 1),
                          _tile(
                            Icons.account_balance,
                            'Bank Account',
                            subtitle: vendor?.bankAccount != null
                                ? '•••• ${vendor!.bankAccount!.substring(vendor.bankAccount!.length > 4 ? vendor.bankAccount!.length - 4 : 0)}'
                                : 'Not Linked',
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),

                    // ── App Info ──
                    Card(
                      child: Column(
                        children: [
                          _tile(
                            Icons.info_outline,
                            'About SVPMS',
                            subtitle: 'v1.0.0',
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),

                    // ── Logout ──
                    _logoutButton(context),
                  ],
                );
              },
            ),
          ),
        );
      },
    );
  }

  Widget _logoutButton(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: () {
        context.read<AuthBloc>().add(LogoutRequested());
      },
      icon: const Icon(Icons.logout, color: AppColors.destructive),
      label: const Text(
        'Sign Out',
        style: TextStyle(color: AppColors.destructive),
      ),
      style: OutlinedButton.styleFrom(
        side: const BorderSide(color: AppColors.destructive),
        padding: const EdgeInsets.symmetric(vertical: 14),
      ),
    );
  }

  Widget _tile(IconData icon, String title, {String? subtitle}) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primary),
      title: Text(title),
      subtitle: subtitle != null
          ? Text(subtitle, style: const TextStyle(fontWeight: FontWeight.w500))
          : null,
    );
  }
}
