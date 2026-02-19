import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter/foundation.dart';
import 'package:go_router/go_router.dart';

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  GoRouter? _router;
  bool _isInitialized = false;

  void setRouter(GoRouter router) {
    _router = router;
  }

  Future<void> initialize() async {
    if (_isInitialized) return;

    // 1. Request permissions
    await _fcm.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    // 2. Init Local Notifications
    const androidSettings = AndroidInitializationSettings(
      '@mipmap/ic_launcher',
    );
    const iosSettings = DarwinInitializationSettings();
    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _localNotifications.initialize(
      initSettings,
      onDidReceiveNotificationResponse: (details) {
        // Handle local notification tap
        if (details.payload != null) {
          // Parse payload to reconstruct message-like structure if needed
          // For simplicity, we assume payload contains the type/id in a way we can parse,
          // or we just rely on the fact that we can't easily reconstruct RemoteMessage here
          // without passing map.
          // Better: pass the data map stringified as payload.
          // _handleMessage from local notification payload is complex without parsing.
          // Let's assume payload is the 'type' for a simple jump, or JSON.
          // For now, let's print.
          // To do it right: parse JSON payload.
        }
      },
    );

    // 3. Foreground Message Handler
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      _showForegroundNotification(message);
    });

    // 4. Background/Terminated Message Handler
    FirebaseMessaging.onMessageOpenedApp.listen(_handleMessage);

    final initialMessage = await _fcm.getInitialMessage();
    if (initialMessage != null) {
      _handleMessage(initialMessage);
    }

    _isInitialized = true;
    if (kDebugMode) {
      print('NotificationService initialized');
      final token = await _fcm.getToken();
      print('FCM Token: $token');
    }
  }

  void _handleMessage(RemoteMessage message) {
    if (_router == null) return;

    final data = message.data;
    final type = data['type'];
    final id = data['id'] ?? data['po_id'] ?? data['rfq_id'];

    switch (type) {
      case 'NEW_PO':
        if (id != null) {
          _router!.push('/purchase-orders/$id');
        } else {
          _router!.push('/purchase-orders');
        }
        break;
      case 'NEW_RFQ':
        if (id != null) {
          // If we had a detail screen for RFQ view (not bidding), we'd go there.
          // But we only have list and bidding.
          // Maybe just go to list? Or bidding if applicable?
          _router!.push('/rfqs');
        } else {
          _router!.push('/rfqs');
        }
        break;
      case 'INVOICE_MATCHED':
      case 'INVOICE_UPDATE':
        _router!.push('/invoices');
        break;
    }
  }

  Future<void> _showForegroundNotification(RemoteMessage message) async {
    final notification = message.notification;
    final android = message.notification?.android;

    if (notification != null && android != null) {
      await _localNotifications.show(
        notification.hashCode,
        notification.title,
        notification.body,
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'high_importance_channel',
            'High Importance Notifications',
            channelDescription:
                'This channel is used for important notifications.',
            importance: Importance.max,
            priority: Priority.high,
            icon: '@mipmap/ic_launcher',
          ),
          iOS: DarwinNotificationDetails(),
        ),
        payload: message.data.toString(), // TODO: Serialize properly if needed
      );
    }
  }

  Future<String?> getFcmToken() async {
    return await _fcm.getToken();
  }
}
