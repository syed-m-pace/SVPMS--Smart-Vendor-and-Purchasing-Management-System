import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:flutter/foundation.dart';

class CrashlyticsBlocObserver extends BlocObserver {
  @override
  void onError(BlocBase bloc, Object error, StackTrace stackTrace) {
    if (!kDebugMode) {
      FirebaseCrashlytics.instance.recordError(error, stackTrace);
    } else {
      debugPrint('Bloc Error in ${bloc.runtimeType}: $error');
    }
    super.onError(bloc, error, stackTrace);
  }
}
