import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../services/notification_service.dart' show NotificationService, AppNotification;

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  List<AppNotification> _notifications = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final items = await NotificationService().getStoredNotifications();
    if (mounted) {
      setState(() {
        _notifications = items;
        _loading = false;
      });
    }
  }

  Future<void> _clearAll() async {
    await NotificationService().clearStoredNotifications();
    if (mounted) setState(() => _notifications = []);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          if (_notifications.isNotEmpty)
            TextButton(
              onPressed: _clearAll,
              child: Text(
                'Clear All',
                style: TextStyle(color: AppColors.textSecondary),
              ),
            ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _notifications.isEmpty
          ? _emptyState()
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView.separated(
                itemCount: _notifications.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, i) => _tile(_notifications[i]),
              ),
            ),
    );
  }

  Widget _tile(AppNotification n) {
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: _iconColor(n.type).withValues(alpha: 0.15),
        child: Icon(_iconData(n.type), color: _iconColor(n.type), size: 20),
      ),
      title: Text(
        n.title,
        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
      ),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (n.body.isNotEmpty)
            Text(n.body, style: const TextStyle(fontSize: 13)),
          const SizedBox(height: 2),
          Text(
            _formatTime(n.receivedAt),
            style: TextStyle(fontSize: 11, color: AppColors.textMuted),
          ),
        ],
      ),
      isThreeLine: n.body.isNotEmpty,
      trailing: n.deepLinkPath != null
          ? Icon(Icons.chevron_right, color: AppColors.textMuted)
          : null,
      onTap: n.deepLinkPath != null
          ? () => context.push(n.deepLinkPath!)
          : null,
    );
  }

  Widget _emptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.notifications_none, size: 64, color: AppColors.textMuted),
          const SizedBox(height: 12),
          Text(
            'No notifications yet',
            style: TextStyle(fontSize: 16, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 4),
          Text(
            "You'll be notified about POs, RFQs, and invoices here.",
            style: TextStyle(fontSize: 13, color: AppColors.textMuted),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  IconData _iconData(String type) {
    switch (type) {
      case 'NEW_PO':
        return Icons.shopping_cart_outlined;
      case 'NEW_RFQ':
        return Icons.gavel;
      case 'INVOICE_MATCHED':
      case 'INVOICE_UPDATE':
        return Icons.receipt_long_outlined;
      case 'PAYMENT':
        return Icons.payments_outlined;
      default:
        return Icons.notifications_outlined;
    }
  }

  Color _iconColor(String type) {
    switch (type) {
      case 'NEW_PO':
        return AppColors.primary;
      case 'NEW_RFQ':
        return AppColors.warning;
      case 'INVOICE_MATCHED':
      case 'INVOICE_UPDATE':
        return AppColors.info;
      case 'PAYMENT':
        return AppColors.success;
      default:
        return AppColors.textSecondary;
    }
  }

  String _formatTime(DateTime dt) {
    final now = DateTime.now();
    final diff = now.difference(dt);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inHours < 1) return '${diff.inMinutes}m ago';
    if (diff.inDays < 1) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return '${dt.day}/${dt.month}/${dt.year}';
  }
}
