import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/datasources/api/api_client.dart';
import 'package:file_picker/file_picker.dart';
import '../../auth/bloc/auth_bloc.dart';
import '../../../data/models/vendor.dart';
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
    final vendor = await client.getVendorMe();
    return Vendor.fromJson(vendor);
  }

  Future<void> _pickImage() async {
    final client = context.read<ApiClient>();
    final result = await FilePicker.platform.pickFiles(type: FileType.image);
    if (result != null && result.files.single.path != null) {
      final filePath = result.files.single.path!;
      try {
        if (!mounted) return;
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Uploading image...')));
        final uploadResp = await client.uploadFile(filePath);
        final key = uploadResp['file_key']; // Store key

        // Update profile
        if (mounted) {
          context.read<AuthBloc>().add(
            UpdateProfileRequested({'profile_photo_url': key}),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Upload failed: $e'),
              backgroundColor: AppColors.destructive,
            ),
          );
        }
      }
    }
  }

  void _showChangePasswordDialog() {
    final currentCtrl = TextEditingController();
    final newCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Change Password'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: currentCtrl,
              decoration: const InputDecoration(labelText: 'Current Password'),
              obscureText: true,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: newCtrl,
              decoration: const InputDecoration(labelText: 'New Password'),
              obscureText: true,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              context.read<AuthBloc>().add(
                ChangePasswordRequested(
                  currentPassword: currentCtrl.text,
                  newPassword: newCtrl.text,
                ),
              );
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Request processed')),
              );
            },
            child: const Text('Change'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<AuthBloc, AuthState>(
      listener: (context, state) {
        if (state is AuthError) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(state.message),
              backgroundColor: AppColors.destructive,
            ),
          );
        }
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
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: AppColors.destructive.withOpacity(0.1),
                              shape: BoxShape.circle,
                            ),
                            child: Icon(
                              Icons.person_off_outlined,
                              size: 48,
                              color: AppColors.destructive,
                            ),
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Failed to load profile',
                            style: GoogleFonts.inter(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Something went wrong while fetching your profile data. Please try again.',
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              fontSize: 14,
                              color: AppColors.textMuted,
                            ),
                          ),
                          const SizedBox(height: 24),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: () => setState(() {
                                _vendorFuture = _fetchVendor();
                              }),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppColors.primary,
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(
                                  vertical: 16,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                              child: const Text('Retry'),
                            ),
                          ),
                          const SizedBox(height: 16),
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton(
                              onPressed: () {
                                context.read<AuthBloc>().add(LogoutRequested());
                              },
                              style: OutlinedButton.styleFrom(
                                side: BorderSide(color: AppColors.destructive),
                                foregroundColor: AppColors.destructive,
                                padding: const EdgeInsets.symmetric(
                                  vertical: 16,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                              child: const Text('Sign Out'),
                            ),
                          ),
                        ],
                      ),
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
                      child: Stack(
                        children: [
                          Container(
                            width: 96,
                            height: 96,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: AppColors.card, // surface -> card
                              border: Border.all(color: AppColors.border),
                              image: user?.profilePhotoUrl != null
                                  ? DecorationImage(
                                      image: NetworkImage(
                                        user!.profilePhotoUrl!,
                                      ),
                                      fit: BoxFit.cover,
                                    )
                                  : null,
                            ),
                            child: user?.profilePhotoUrl == null
                                ? Center(
                                    child: Text(
                                      vendor?.legalName.isNotEmpty == true
                                          ? vendor!.legalName[0].toUpperCase()
                                          : '?',
                                      style: GoogleFonts.inter(
                                        fontSize: 32,
                                        fontWeight: FontWeight.w700,
                                        color: AppColors.primary,
                                      ),
                                    ),
                                  )
                                : null,
                          ),
                          Positioned(
                            bottom: 0,
                            right: 0,
                            child: InkWell(
                              onTap: _pickImage,
                              child: Container(
                                padding: const EdgeInsets.all(6),
                                decoration: const BoxDecoration(
                                  color: AppColors.primary,
                                  shape: BoxShape.circle,
                                ),
                                child: const Icon(
                                  Icons.camera_alt,
                                  size: 16,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 24),
                    Center(
                      child: Text(
                        vendor?.legalName ?? 'Unknown Vendor',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(
                          fontSize: 24,
                          fontWeight: FontWeight.w800,
                          color: AppColors.textPrimary,
                          letterSpacing: -0.5,
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    if (vendor?.status != null)
                      Center(child: StatusBadge(status: vendor!.status)),
                    const SizedBox(height: 12),
                    Center(
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.card,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Text(
                          user?.email ?? vendor?.email ?? '',
                          style: GoogleFonts.inter(
                            fontSize: 14,
                            color: AppColors.textMuted,
                            fontWeight: FontWeight.w500,
                          ),
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
                            Icons.lock_outline,
                            'Change Password',
                            onTap: _showChangePasswordDialog,
                          ),
                          const Divider(height: 1),
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

  Widget _tile(
    IconData icon,
    String title, {
    String? subtitle,
    VoidCallback? onTap,
  }) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primary),
      title: Text(title),
      subtitle: subtitle != null
          ? Text(subtitle, style: const TextStyle(fontWeight: FontWeight.w500))
          : null,
      onTap: onTap,
      trailing: onTap != null ? const Icon(Icons.chevron_right) : null,
    );
  }
}
