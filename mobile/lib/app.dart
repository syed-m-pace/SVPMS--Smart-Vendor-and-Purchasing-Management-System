import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'core/constants/app_theme.dart';
import 'core/router/app_router.dart';
import 'data/datasources/api/api_client.dart';
import 'data/repositories/auth_repository.dart';
import 'data/repositories/dashboard_repository.dart';
import 'data/repositories/invoice_repository.dart';
import 'data/repositories/po_repository.dart';
import 'data/repositories/rfq_repository.dart';
import 'presentation/auth/bloc/auth_bloc.dart';
import 'presentation/dashboard/bloc/dashboard_bloc.dart';
import 'presentation/invoices/bloc/invoice_bloc.dart';
import 'presentation/purchase_orders/bloc/po_bloc.dart';
import 'presentation/rfqs/bloc/rfq_bloc.dart';
import 'services/local_cache_service.dart';
import 'services/storage_service.dart';

class SVPMSApp extends StatelessWidget {
  final LocalCacheService localCache;
  final StorageService? storageService;
  final AuthRepository? authRepository;

  const SVPMSApp({
    super.key,
    required this.localCache,
    this.storageService,
    this.authRepository,
  });

  @override
  Widget build(BuildContext context) {
    final storage = storageService ?? StorageService();
    final apiClient = ApiClient(storage: storage);

    final authRepo =
        authRepository ??
        AuthRepository(api: apiClient, storage: storage, cache: localCache);
    final dashboardRepo = DashboardRepository(
      api: apiClient,
      cache: localCache,
    );
    final poRepo = PORepository(api: apiClient, cache: localCache);
    final rfqRepo = RFQRepository(api: apiClient, cache: localCache);

    final invoiceRepo = InvoiceRepository(
      api: apiClient,
    ); // Not caching invoices yet

    // Create AuthBloc first — router needs it for refreshListenable
    final authBloc = AuthBloc(repo: authRepo)..add(CheckAuth());

    return MultiRepositoryProvider(
      providers: [
        RepositoryProvider<StorageService>.value(value: storage),
        RepositoryProvider<ApiClient>.value(value: apiClient),
        RepositoryProvider<AuthRepository>.value(value: authRepo),
        RepositoryProvider<DashboardRepository>.value(value: dashboardRepo),
        RepositoryProvider<PORepository>.value(value: poRepo),
        RepositoryProvider<InvoiceRepository>.value(value: invoiceRepo),
        RepositoryProvider<RFQRepository>.value(value: rfqRepo),
        RepositoryProvider<LocalCacheService>.value(value: localCache),
      ],
      child: MultiBlocProvider(
        providers: [
          BlocProvider.value(value: authBloc),
          BlocProvider(
            create: (_) =>
                DashboardBloc(repo: dashboardRepo)..add(LoadDashboard()),
          ),
          BlocProvider(create: (_) => POBloc(repo: poRepo)..add(LoadPOs())),
          BlocProvider(
            create: (_) => InvoiceBloc(repo: invoiceRepo)..add(LoadInvoices()),
          ),
          BlocProvider(create: (_) => RFQBloc(repo: rfqRepo)..add(LoadRFQs())),
        ],
        child: MaterialApp.router(
          title: 'SVPMS Vendor Portal',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light,
          routerConfig: createRouter(storage, authBloc),
        ),
      ),
    );
  }
}
