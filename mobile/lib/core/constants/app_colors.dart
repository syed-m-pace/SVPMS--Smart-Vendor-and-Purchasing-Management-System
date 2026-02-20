import 'package:flutter/material.dart';

/// Unified design system colors — shared with Next.js admin dashboard (Phase 6)
class AppColors {
  AppColors._();

  // ── Primary ──
  static const Color primary = Color(0xFF2A3F5F); // Deep navy
  static const Color primaryLight = Color(0xFF3D5A80);
  static const Color primaryDark = Color(0xFF1B2A40);

  // ── Accent ──
  static const Color accent = Color(0xFF0EA5E9); // Sky blue
  static const Color accentLight = Color(0xFF38BDF8);

  // ── Semantic ──
  static const Color success = Color(0xFF22C55E);
  static const Color warning = Color.fromARGB(255, 244, 180, 69);
  static const Color destructive = Color(0xFFEF4444);
  static const Color info = Color(0xFF8B5CF6); // Violet

  // ── Surfaces ──
  static const Color background = Color(0xFFF8FAFC);
  static const Color card = Color(0xFFFFFFFF);
  static const Color muted = Color(0xFFF1F5F9);
  static const Color border = Color(0xFFE2E8F0);

  // ── Text ──
  static const Color textPrimary = Color(0xFF0F172A);
  static const Color textSecondary = Color(0xFF64748B);
  static const Color textMuted = Color(0xFF94A3B8);
  static const Color textOnPrimary = Color(0xFFFFFFFF);

  // ── Sidebar (matches web) ──
  static const Color sidebar = Color(0xFF1E3050);

  /// Map entity status → color
  static Color statusColor(String status) {
    switch (status.toUpperCase()) {
      case 'DRAFT':
        return warning;
      case 'PENDING':
      case 'PENDING_APPROVAL':
        return warning;
      case 'APPROVED':
      case 'ACTIVE':
      case 'MATCHED':
        return success;
      case 'REJECTED':
      case 'BLOCKED':
      case 'EXCEPTION':
        return destructive;
      case 'ISSUED':
      case 'ACKNOWLEDGED':
        return accent;
      case 'OPEN':
        return info;
      default:
        return textSecondary;
    }
  }
}
