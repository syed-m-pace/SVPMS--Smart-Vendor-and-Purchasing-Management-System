import 'package:flutter/foundation.dart'
    show kIsWeb, TargetPlatform, defaultTargetPlatform;

class ApiConstants {
  ApiConstants._();

  /// Base URL — uses 10.0.2.2 for Android emulator, localhost for iOS sim / desktop / web
  static const bool useProduction = true;

  static String get baseUrl {
    if (useProduction) {
      return 'https://svpms-be-gcloud-325948496969.asia-south1.run.app';
    }
    if (kIsWeb) {
      return 'http://localhost:8000';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://localhost:8000';
  }

  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
}
