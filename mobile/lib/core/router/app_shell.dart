import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:svpms_vendor/data/datasources/api/api_client.dart';
import 'package:svpms_vendor/data/models/vendor.dart';
import 'package:svpms_vendor/presentation/widgets/status_badge.dart';
import '../../presentation/auth/bloc/auth_bloc.dart';

/// Shell widget containing bottom navigation bar and app bar
class AppShell extends StatefulWidget {
  final Widget child;
  const AppShell({super.key, required this.child});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  late Future<Vendor> _vendorFuture;

  @override
  void initState() {
    super.initState();
    _vendorFuture = _fetchVendor();
  }

  Future<Vendor> _fetchVendor() async {
    final client = context.read<ApiClient>();
    final vendor = await client.getVendorMe();
    return Vendor.fromJson(vendor);
  }

  static const _tabs = [
    '/dashboard',
    '/purchase-orders',
    '/rfqs',
    '/invoices',
    '/profile',
  ];

  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    for (int i = 0; i < _tabs.length; i++) {
      if (location.startsWith(_tabs[i])) return i;
    }
    return 0;
  }

  String _title(int index) {
    switch (index) {
      case 0:
        return 'Dashboard';
      case 1:
        return 'Purchase Orders';
      case 2:
        return 'RFQs';
      case 3:
        return 'Invoices';
      case 4:
        return 'Profile';
      default:
        return 'SVPMS';
    }
  }

  @override
  Widget build(BuildContext context) {
    final index = _currentIndex(context);

    return BlocListener<AuthBloc, AuthState>(
      listener: (context, state) {
        if (state is Unauthenticated) {
          context.go('/login');
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(_title(index)),
          actions: [
            if (index == 0) // dashboard tab
              IconButton(
                icon: const Icon(Icons.notifications),
                tooltip: 'Notifications',
                onPressed: () {
                  // Placeholder for notifications
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('No new notifications')),
                  );
                },
              ),
            FutureBuilder<Vendor>(
              future: _vendorFuture,
              builder: (context, snapshot) {
                if (snapshot.hasData && snapshot.data?.status != null) {
                  return Padding(
                    padding: const EdgeInsets.only(right: 16.0),
                    child: Center(
                      child: StatusBadge(status: snapshot.data!.status),
                    ),
                  );
                }
                return const SizedBox.shrink();
              },
            ),
          ],
        ),
        body: widget.child,
        floatingActionButton: index == 3
            ? FloatingActionButton(
                onPressed: () => context.push('/invoices/upload'),
                tooltip: 'Upload Invoice',
                child: const Icon(Icons.upload),
              )
            : null,
        bottomNavigationBar: MediaQuery.removePadding(
          context: context,
          removeBottom: true,
          child: BottomNavigationBar(
            type: BottomNavigationBarType.fixed,
            currentIndex: index,
            onTap: (i) => context.go(_tabs[i]),
            items: const [
              BottomNavigationBarItem(
                icon: Icon(Icons.dashboard),
                label: 'Dashboard',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.shopping_cart),
                label: 'Orders',
              ),
              BottomNavigationBarItem(icon: Icon(Icons.gavel), label: 'RFQs'),
              BottomNavigationBarItem(
                icon: Icon(Icons.receipt_long),
                label: 'Invoices',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.person),
                label: 'Profile',
              ),
            ],
          ),
        ),
      ),
    );
  }
}
