import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/data/repositories/contract_repository.dart';
import '../../helpers/mocks.dart';
import '../../helpers/fixtures.dart';

void main() {
  late MockApiClient mockApi;
  late ContractRepository repo;

  setUp(() {
    mockApi = MockApiClient();
    repo = ContractRepository(api: mockApi);
  });

  group('list', () {
    test('returns contracts from data key', () async {
      when(() => mockApi.getContracts(page: 1)).thenAnswer(
        (_) async => {'data': [makeContractJson()]},
      );

      final contracts = await repo.list();
      expect(contracts.length, 1);
      expect(contracts.first.title, 'Annual Supply Agreement');
    });

    test('returns contracts from items key', () async {
      when(() => mockApi.getContracts(page: 1)).thenAnswer(
        (_) async => {'items': [makeContractJson(id: 'c-002')]},
      );

      final contracts = await repo.list();
      expect(contracts.length, 1);
      expect(contracts.first.id, 'c-002');
    });

    test('passes status filter', () async {
      when(() => mockApi.getContracts(status: 'ACTIVE', page: 1)).thenAnswer(
        (_) async => {'data': [makeContractJson()]},
      );

      final contracts = await repo.list(status: 'ACTIVE');
      expect(contracts.length, 1);
    });
  });

  group('getById', () {
    test('returns single contract', () async {
      when(() => mockApi.getContract('c-001'))
          .thenAnswer((_) async => makeContractJson());

      final c = await repo.getById('c-001');
      expect(c.id, 'c-001');
      expect(c.contractNumber, 'CON-2026-001');
    });
  });
}
