import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/data/models/user.dart';
import '../../helpers/fixtures.dart';

void main() {
  group('User.fromJson', () {
    test('parses all fields correctly', () {
      final json = makeUserJson();
      final user = User.fromJson(json);
      expect(user.id, 'u-001');
      expect(user.email, 'vendor@test.com');
      expect(user.role, 'vendor');
      expect(user.firstName, 'Test');
      expect(user.lastName, 'Vendor');
      expect(user.isActive, true);
      expect(user.departmentId, isNull);
      expect(user.profilePhotoUrl, isNull);
    });

    test('handles null optional fields', () {
      final json = {
        'id': 'u-002',
        'email': 'test@test.com',
        'role': 'admin',
        'is_active': false,
      };
      final user = User.fromJson(json);
      expect(user.firstName, isNull);
      expect(user.lastName, isNull);
      expect(user.isActive, false);
    });

    test('defaults is_active to true when missing', () {
      final json = {'id': 'u-003', 'email': 'a@b.com', 'role': 'vendor'};
      final user = User.fromJson(json);
      expect(user.isActive, true);
    });

    test('fullName concatenates first and last', () {
      final user = User.fromJson(makeUserJson(firstName: 'John', lastName: 'Doe'));
      expect(user.fullName, 'John Doe');
    });
  });
}
