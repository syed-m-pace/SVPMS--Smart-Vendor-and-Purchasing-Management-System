import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/core/constants/app_colors.dart';

void main() {
  group('AppColors.statusColor', () {
    test('DRAFT returns warning', () {
      expect(AppColors.statusColor('DRAFT'), AppColors.warning);
    });

    test('PENDING returns warning', () {
      expect(AppColors.statusColor('PENDING'), AppColors.warning);
    });

    test('PENDING_APPROVAL returns warning', () {
      expect(AppColors.statusColor('PENDING_APPROVAL'), AppColors.warning);
    });

    test('APPROVED returns success', () {
      expect(AppColors.statusColor('APPROVED'), AppColors.success);
    });

    test('ACTIVE returns success', () {
      expect(AppColors.statusColor('ACTIVE'), AppColors.success);
    });

    test('MATCHED returns success', () {
      expect(AppColors.statusColor('MATCHED'), AppColors.success);
    });

    test('REJECTED returns destructive', () {
      expect(AppColors.statusColor('REJECTED'), AppColors.destructive);
    });

    test('BLOCKED returns destructive', () {
      expect(AppColors.statusColor('BLOCKED'), AppColors.destructive);
    });

    test('EXCEPTION returns destructive', () {
      expect(AppColors.statusColor('EXCEPTION'), AppColors.destructive);
    });

    test('ISSUED returns accent', () {
      expect(AppColors.statusColor('ISSUED'), AppColors.accent);
    });

    test('ACKNOWLEDGED returns accent', () {
      expect(AppColors.statusColor('ACKNOWLEDGED'), AppColors.accent);
    });

    test('OPEN returns info', () {
      expect(AppColors.statusColor('OPEN'), AppColors.info);
    });

    test('unknown status returns textSecondary', () {
      expect(AppColors.statusColor('UNKNOWN'), AppColors.textSecondary);
    });

    test('is case-insensitive', () {
      expect(AppColors.statusColor('approved'), AppColors.success);
      expect(AppColors.statusColor('Rejected'), AppColors.destructive);
    });
  });
}
