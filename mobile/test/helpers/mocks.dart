import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/data/datasources/api/api_client.dart';
import 'package:svpms_vendor/data/repositories/auth_repository.dart';
import 'package:svpms_vendor/data/repositories/dashboard_repository.dart';
import 'package:svpms_vendor/data/repositories/po_repository.dart';
import 'package:svpms_vendor/data/repositories/invoice_repository.dart';
import 'package:svpms_vendor/data/repositories/rfq_repository.dart';
import 'package:svpms_vendor/data/repositories/contract_repository.dart';
import 'package:svpms_vendor/services/local_cache_service.dart';
import 'package:svpms_vendor/services/storage_service.dart';

class MockAuthRepository extends Mock implements AuthRepository {}

class MockDashboardRepository extends Mock implements DashboardRepository {}

class MockPORepository extends Mock implements PORepository {}

class MockInvoiceRepository extends Mock implements InvoiceRepository {}

class MockRFQRepository extends Mock implements RFQRepository {}

class MockContractRepository extends Mock implements ContractRepository {}

class MockLocalCacheService extends Mock implements LocalCacheService {}

class MockStorageService extends Mock implements StorageService {}

class MockApiClient extends Mock implements ApiClient {}

class MockDio extends Mock implements Dio {}

class MockFlutterSecureStorage extends Mock implements FlutterSecureStorage {}
