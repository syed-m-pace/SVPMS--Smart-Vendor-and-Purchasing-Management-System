import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/constants/app_colors.dart';
import '../../auth/bloc/auth_bloc.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<AuthBloc, AuthState>(
      builder: (context, state) {
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
                    user != null
                        ? user.fullName
                              .split(' ')
                              .map((w) => w.isNotEmpty ? w[0] : '')
                              .take(2)
                              .join()
                              .toUpperCase()
                        : '?',
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
                user?.fullName ?? 'Unknown',
                style: GoogleFonts.inter(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
            Center(
              child: Text(
                user?.role ?? '',
                style: TextStyle(fontSize: 14, color: AppColors.textSecondary),
              ),
            ),
            const SizedBox(height: 4),
            Center(
              child: Text(
                user?.email ?? '',
                style: TextStyle(fontSize: 13, color: AppColors.textMuted),
              ),
            ),
            const SizedBox(height: 32),

            // ── Menu items ──
            Card(
              child: Column(
                children: [
                  _tile(Icons.business, 'Organization', subtitle: 'ACME Corp'),
                  const Divider(height: 1),
                  _tile(Icons.notifications_outlined, 'Notifications'),
                  const Divider(height: 1),
                  _tile(Icons.security_outlined, 'Security'),
                  const Divider(height: 1),
                  _tile(Icons.info_outline, 'About SVPMS', subtitle: 'v1.0.0'),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // ── Logout ──
            OutlinedButton.icon(
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
            ),
          ],
        );
      },
    );
  }

  Widget _tile(IconData icon, String title, {String? subtitle}) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primary),
      title: Text(title),
      subtitle: subtitle != null ? Text(subtitle) : null,
      trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted),
    );
  }
}
