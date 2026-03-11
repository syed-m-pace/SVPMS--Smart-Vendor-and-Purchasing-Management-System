import 'package:flutter_test/flutter_test.dart';
import 'package:svpms_vendor/core/constants/api_constants.dart';

void main() {
  group('ApiConstants', () {
    test('baseUrl returns production URL when useProduction is true', () {
      // useProduction is const true in the source
      expect(ApiConstants.baseUrl, contains('svpms'));
    });

    test('connectTimeout is 30 seconds', () {
      expect(ApiConstants.connectTimeout, const Duration(seconds: 30));
    });

    test('receiveTimeout is 30 seconds', () {
      expect(ApiConstants.receiveTimeout, const Duration(seconds: 30));
    });
  });
}
