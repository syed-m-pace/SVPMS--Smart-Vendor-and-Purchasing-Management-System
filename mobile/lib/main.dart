import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'services/local_cache_service.dart';
import 'services/notification_service.dart';
import 'core/observers/crashlytics_bloc_observer.dart';
import 'app.dart';
import 'firebase_options.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 1. Initialize Firebase
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  // 2. Initialize Crashlytics
  FlutterError.onError = (errorDetails) {
    FirebaseCrashlytics.instance.recordFlutterFatalError(errorDetails);
  };
  // Pass all uncaught asynchronous errors that aren't handled by the Flutter framework to Crashlytics
  PlatformDispatcher.instance.onError = (error, stack) {
    FirebaseCrashlytics.instance.recordError(error, stack, fatal: true);
    return true;
  };

  // 3. Initialize Hive (Local Cache)
  final localCache = LocalCacheService();
  await localCache.init();

  // 4. Initialize Notifications (FCM)
  if (Platform.isAndroid || Platform.isIOS) {
    await NotificationService().initialize();
  }

  // 5. Bloc Observer
  Bloc.observer = CrashlyticsBlocObserver();

  // 6. Run App
  runApp(SVPMSApp(localCache: localCache));
}
