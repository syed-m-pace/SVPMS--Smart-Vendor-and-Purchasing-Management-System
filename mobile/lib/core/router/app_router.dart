import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/storage_service.dart';
import '../../presentation/auth/bloc/auth_bloc.dart';
import '../../presentation/auth/screens/login_screen.dart';
import '../../presentation/dashboard/screens/dashboard_screen.dart';
import '../../presentation/purchase_orders/screens/po_list_screen.dart';
import '../../presentation/purchase_orders/screens/po_detail_screen.dart';
import '../../presentation/rfqs/screens/rfq_list_screen.dart';
import '../../presentation/rfqs/screens/rfq_bidding_screen.dart';
import '../../presentation/invoices/screens/invoice_list_screen.dart';
import '../../presentation/invoices/screens/invoice_upload_screen.dart';
import '../../presentation/invoices/screens/invoice_detail_screen.dart';
import '../../presentation/profile/screens/profile_screen.dart';
import 'app_shell.dart';

import '../../services/notification_service.dart';

/// Bridges AuthBloc state changes → GoRouter.refresh so the redirect runs
/// whenever auth state changes (login, logout).
class AuthNotifier extends ChangeNotifier {
  AuthNotifier(AuthBloc authBloc) {
    authBloc.stream.listen((_) => notifyListeners());
  }
}

GoRouter createRouter(StorageService storage, AuthBloc authBloc) {
  final authNotifier = AuthNotifier(authBloc);

  final router = GoRouter(
    initialLocation: '/dashboard',
    refreshListenable: authNotifier,
    redirect: (context, state) async {
      final authState = authBloc.state;
      bool loggedIn;
      if (authState is Authenticated) {
        loggedIn = true;
      } else if (authState is Unauthenticated || authState is AuthError) {
        loggedIn = false;
      } else {
        loggedIn = await storage.hasTokens;
      }
      final onLogin = state.matchedLocation == '/login';
      if (!loggedIn && !onLogin) return '/login';
      if (loggedIn && onLogin) return '/dashboard';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: '/dashboard',
            builder: (context, state) => const DashboardScreen(),
          ),
          GoRoute(
            path: '/purchase-orders',
            builder: (context, state) => const POListScreen(),
          ),
          GoRoute(
            path: '/rfqs',
            builder: (context, state) => const RFQListScreen(),
            routes: [
              GoRoute(
                path: ':id/bid',
                builder: (context, state) =>
                    RFQBiddingScreen(rfqId: state.pathParameters['id']!),
              ),
            ],
          ),
          GoRoute(
            path: '/invoices',
            builder: (context, state) => const InvoiceListScreen(),
          ),

          GoRoute(
            path: '/profile',
            builder: (context, state) => const ProfileScreen(),
          ),
        ],
      ),
      GoRoute(
        path: '/purchase-orders/:id',
        builder: (context, state) =>
            PODetailScreen(poId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/invoices/upload',
        builder: (context, state) => const InvoiceUploadScreen(),
      ),
      GoRoute(
        path: '/invoices/:id',
        builder: (context, state) =>
            InvoiceDetailScreen(invoiceId: state.pathParameters['id']!),
      ),
    ],
  );

  NotificationService().setRouter(router);
  return router;
}
