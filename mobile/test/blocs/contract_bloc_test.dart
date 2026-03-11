import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/presentation/contracts/bloc/contract_bloc.dart';

import '../helpers/mocks.dart';
import '../helpers/fixtures.dart';

void main() {
  late MockContractRepository mockRepo;

  setUp(() {
    mockRepo = MockContractRepository();
  });

  group('ContractBloc', () {
    blocTest<ContractBloc, ContractState>(
      'emits [ContractLoading, ContractListLoaded] on LoadContracts',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: any(named: 'page')))
            .thenAnswer((_) async => [makeContract()]);
        return ContractBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadContracts()),
      expect: () => [
        isA<ContractLoading>(),
        isA<ContractListLoaded>()
            .having((s) => s.contracts.length, 'count', 1)
            .having((s) => s.hasMore, 'hasMore', false),
      ],
    );

    blocTest<ContractBloc, ContractState>(
      'emits [ContractLoading, ContractListLoaded] with status filter',
      build: () {
        when(() => mockRepo.list(status: 'ACTIVE', page: 1))
            .thenAnswer((_) async => [makeContract(status: 'ACTIVE')]);
        return ContractBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadContracts(status: 'ACTIVE')),
      expect: () => [
        isA<ContractLoading>(),
        isA<ContractListLoaded>()
            .having((s) => s.contracts.first.status, 'status', 'ACTIVE'),
      ],
    );

    blocTest<ContractBloc, ContractState>(
      'emits [ContractLoading, ContractDetailLoaded] on LoadContractDetail',
      build: () {
        when(() => mockRepo.getById(any()))
            .thenAnswer((_) async => makeContract());
        return ContractBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadContractDetail('c-001')),
      expect: () => [
        isA<ContractLoading>(),
        isA<ContractDetailLoaded>(),
      ],
    );

    blocTest<ContractBloc, ContractState>(
      'emits [ContractLoading, ContractError] when LoadContracts fails',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: any(named: 'page')))
            .thenThrow(Exception('Network error'));
        return ContractBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadContracts()),
      expect: () => [
        isA<ContractLoading>(),
        isA<ContractError>(),
      ],
    );

    blocTest<ContractBloc, ContractState>(
      'LoadMoreContracts appends and increments page',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 2))
            .thenAnswer((_) async => [makeContract(id: 'c-new')]);
        return ContractBloc(repo: mockRepo);
      },
      seed: () => ContractListLoaded(
        [makeContract()],
        hasMore: true,
        page: 1,
      ),
      act: (bloc) => bloc.add(LoadMoreContracts()),
      expect: () => [
        isA<ContractListLoaded>().having((s) => s.isLoadingMore, 'loading', true),
        isA<ContractListLoaded>()
            .having((s) => s.contracts.length, 'count', 2)
            .having((s) => s.page, 'page', 2),
      ],
    );

    blocTest<ContractBloc, ContractState>(
      'LoadMoreContracts does nothing when hasMore is false',
      build: () => ContractBloc(repo: mockRepo),
      seed: () => ContractListLoaded([makeContract()], hasMore: false, page: 1),
      act: (bloc) => bloc.add(LoadMoreContracts()),
      expect: () => [],
    );

    blocTest<ContractBloc, ContractState>(
      'LoadMoreContracts recovers on error',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 2))
            .thenThrow(Exception('Network error'));
        return ContractBloc(repo: mockRepo);
      },
      seed: () => ContractListLoaded([makeContract()], hasMore: true, page: 1),
      act: (bloc) => bloc.add(LoadMoreContracts()),
      expect: () => [
        isA<ContractListLoaded>().having((s) => s.isLoadingMore, 'loading', true),
        isA<ContractListLoaded>()
            .having((s) => s.contracts.length, 'count', 1)
            .having((s) => s.page, 'page', 1),
      ],
    );

    blocTest<ContractBloc, ContractState>(
      'RefreshContracts emits ContractListLoaded',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 1))
            .thenAnswer((_) async => [makeContract()]);
        return ContractBloc(repo: mockRepo);
      },
      seed: () => ContractListLoaded([makeContract()], hasMore: false, page: 1),
      act: (bloc) => bloc.add(RefreshContracts()),
      expect: () => [isA<ContractListLoaded>()],
    );

    blocTest<ContractBloc, ContractState>(
      'RefreshContracts emits ContractError on failure',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 1))
            .thenThrow(Exception('Timeout'));
        return ContractBloc(repo: mockRepo);
      },
      seed: () => ContractListLoaded([makeContract()], hasMore: false, page: 1),
      act: (bloc) => bloc.add(RefreshContracts()),
      expect: () => [isA<ContractError>()],
    );

    blocTest<ContractBloc, ContractState>(
      'LoadContractDetail emits ContractError on failure',
      build: () {
        when(() => mockRepo.getById(any()))
            .thenThrow(Exception('Not found'));
        return ContractBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadContractDetail('c-999')),
      expect: () => [
        isA<ContractLoading>(),
        isA<ContractError>(),
      ],
    );
  });
}
