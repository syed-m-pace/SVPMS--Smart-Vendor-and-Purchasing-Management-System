import 'dart:convert';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter/foundation.dart';
import 'package:go_router/go_router.dart';
import 'package:hive_flutter/hive_flutter.dart';

/// Lightweight value object for a persisted notification.
class AppNotification {
  final String id;
  final String title;
  final String body;
  final String type;
  final String? deepLinkPath;
  final DateTime receivedAt;

  const AppNotification({
    required this.id,
    required this.title,
    required this.body,
    required this.type,
    this.deepLinkPath,
    required this.receivedAt,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'body': body,
    'type': type,
    'deepLinkPath': deepLinkPath,
    'receivedAt': receivedAt.toIso8601String(),
  };

  factory AppNotification.fromJson(Map<String, dynamic> json) =>
      AppNotification(
        id: json['id'] ?? '',
        title: json['title'] ?? '',
        body: json['body'] ?? '',
        type: json['type'] ?? 'GENERIC',
        deepLinkPath: json['deepLinkPath'],
        receivedAt:
            DateTime.tryParse(json['receivedAt'] ?? '') ?? DateTime.now(),
      );
}

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  static const _hiveBoxName = 'svpms_notifications';
  static const _hiveKey = 'notifications_list';
  static const _maxStored = 50;

  final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  GoRouter? _router;
  bool _isInitialized = false;
  Future<void> Function(String token)? _onTokenRefresh;

  void setRouter(GoRouter router) {
    _router = router;
  }

  void setOnTokenRefresh(Future<void> Function(String token) callback) {
    _onTokenRefresh = callback;
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
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );
    await _localNotifications.initialize(
      const InitializationSettings(android: androidSettings, iOS: iosSettings),
    );

    // 3. Foreground Message Handler
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      _storeNotification(message);
      _showForegroundNotification(message);
    });

    // 4. Background/Terminated Message Handler
    FirebaseMessaging.onMessageOpenedApp.listen((msg) {
      _storeNotification(msg);
      _handleMessage(msg);
    });

    _fcm.onTokenRefresh.listen((token) {
      final callback = _onTokenRefresh;
      if (callback != null) callback(token);
    });

    final initialMessage = await _fcm.getInitialMessage();
    if (initialMessage != null) {
      _storeNotification(initialMessage);
      _handleMessage(initialMessage);
    }

    _isInitialized = true;
    if (kDebugMode) {
      print('NotificationService initialized');
      final token = await _fcm.getToken();
      print('FCM Token: $token');
    }
  }

  // ─── Notification Storage ─────────────────────────────────────────────────

  Future<void> _storeNotification(RemoteMessage message) async {
    try {
      final notification = message.notification;
      final data = message.data;
      final type = data['type'] ?? 'GENERIC';
      final id = data['id'] ?? data['po_id'] ?? data['rfq_id'];

      final appNotif = AppNotification(
        id:
            message.messageId ??
            DateTime.now().millisecondsSinceEpoch.toString(),
        title: notification?.title ?? _defaultTitle(type),
        body: notification?.body ?? '',
        type: type,
        deepLinkPath: _buildDeepLink(type, id),
        receivedAt: DateTime.now(),
      );

      final box = await Hive.openBox(_hiveBoxName);
      final raw = box.get(_hiveKey, defaultValue: '[]') as String;
      final List<dynamic> list = jsonDecode(raw);
      list.insert(0, appNotif.toJson());
      // Cap stored notifications
      final trimmed = list.take(_maxStored).toList();
      await box.put(_hiveKey, jsonEncode(trimmed));
    } catch (e) {
      if (kDebugMode) print('NotificationService._storeNotification error: $e');
    }
  }

  Future<List<AppNotification>> getStoredNotifications() async {
    try {
      final box = await Hive.openBox(_hiveBoxName);
      final raw = box.get(_hiveKey, defaultValue: '[]') as String;
      final List<dynamic> list = jsonDecode(raw);
      return list
          .map((e) => AppNotification.fromJson(Map<String, dynamic>.from(e)))
          .toList();
    } catch (e) {
      return [];
    }
  }

  Future<void> clearStoredNotifications() async {
    try {
      final box = await Hive.openBox(_hiveBoxName);
      await box.put(_hiveKey, '[]');
    } catch (e) {
      if (kDebugMode) print('NotificationService.clearStored error: $e');
    }
  }

  final int _unreadCount = 0;
  int get unreadCount => _unreadCount;

  // ─── Deep Link Routing ────────────────────────────────────────────────────

  String? _buildDeepLink(String type, String? id) {
    switch (type) {
      case 'NEW_PO':
        return id != null ? '/purchase-orders/$id' : '/purchase-orders';
      case 'NEW_RFQ':
        return id != null ? '/rfqs/$id' : '/rfqs';
      case 'INVOICE_MATCHED':
      case 'INVOICE_UPDATE':
        return id != null ? '/invoices/$id' : '/invoices';
      default:
        return null;
    }
  }

  String _defaultTitle(String type) {
    switch (type) {
      case 'NEW_PO':
        return 'New Purchase Order';
      case 'NEW_RFQ':
        return 'New RFQ Invitation';
      case 'INVOICE_MATCHED':
        return 'Invoice Matched';
      case 'INVOICE_UPDATE':
        return 'Invoice Updated';
      default:
        return 'SVPMS Notification';
    }
  }

  void _handleMessage(RemoteMessage message) {
    if (_router == null) return;
    final data = message.data;
    final type = data['type'];
    final id = data['id'] ?? data['po_id'] ?? data['rfq_id'];
    final deepLink = _buildDeepLink(type ?? '', id);
    if (deepLink != null) {
      _router!.push(deepLink);
    }
  }

  Future<void> _showForegroundNotification(RemoteMessage message) async {
    final notification = message.notification;
    if (notification == null) return;

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
        iOS: DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: true,
        ),
      ),
      payload: message.data.toString(),
    );
  }

  Future<String?> getFcmToken() async {
    return await _fcm.getToken();
  }
}
