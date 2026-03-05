import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/presentation/purchase_orders/bloc/po_bloc.dart';

import '../helpers/mocks.dart';
import '../helpers/fixtures.dart';

void main() {
  late MockPORepository mockRepo;

  setUp(() {
    mockRepo = MockPORepository();
  });

  group('POBloc', () {
    blocTest<POBloc, POState>(
      'emits [POLoading, POListLoaded] on LoadPOs',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: any(named: 'page')))
            .thenAnswer((_) async => [makePurchaseOrder()]);
        return POBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadPOs()),
      expect: () => [
        isA<POLoading>(),
        isA<POListLoaded>()
            .having((s) => s.orders.length, 'count', 1)
            .having((s) => s.page, 'page', 1)
            .having((s) => s.hasMore, 'hasMore', false),
      ],
    );

    blocTest<POBloc, POState>(
      'emits [POLoading, POListLoaded] with status filter',
      build: () {
        when(() => mockRepo.list(status: 'ISSUED', page: 1))
            .thenAnswer((_) async => [makePurchaseOrder(status: 'ISSUED')]);
        return POBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadPOs(status: 'ISSUED')),
      expect: () => [
        isA<POLoading>(),
        isA<POListLoaded>()
            .having((s) => s.orders.first.status, 'status', 'ISSUED'),
      ],
    );

    blocTest<POBloc, POState>(
      'hasMore is true when 20+ items returned',
      build: () {
        final orders = makeList(20, (i) => makePurchaseOrder(id: 'po-$i'));
        when(() => mockRepo.list(status: any(named: 'status'), page: any(named: 'page')))
            .thenAnswer((_) async => orders);
        return POBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadPOs()),
      expect: () => [
        isA<POLoading>(),
        isA<POListLoaded>().having((s) => s.hasMore, 'hasMore', true),
      ],
    );

    blocTest<POBloc, POState>(
      'LoadMorePOs appends items and increments page',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 2))
            .thenAnswer((_) async => [makePurchaseOrder(id: 'po-new')]);
        return POBloc(repo: mockRepo);
      },
      seed: () => POListLoaded(
        [makePurchaseOrder()],
        hasMore: true,
        page: 1,
      ),
      act: (bloc) => bloc.add(LoadMorePOs()),
      expect: () => [
        isA<POListLoaded>().having((s) => s.isLoadingMore, 'loading', true),
        isA<POListLoaded>()
            .having((s) => s.orders.length, 'count', 2)
            .having((s) => s.page, 'page', 2),
      ],
    );

    blocTest<POBloc, POState>(
      'LoadMorePOs does nothing when hasMore is false',
      build: () => POBloc(repo: mockRepo),
      seed: () => POListLoaded([makePurchaseOrder()], hasMore: false, page: 1),
      act: (bloc) => bloc.add(LoadMorePOs()),
      expect: () => [],
    );

    blocTest<POBloc, POState>(
      'emits [POLoading, PODetailLoaded] on LoadPODetail',
      build: () {
        when(() => mockRepo.getById(any()))
            .thenAnswer((_) async => makePurchaseOrder());
        return POBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadPODetail('po-001')),
      expect: () => [
        isA<POLoading>(),
        isA<PODetailLoaded>(),
      ],
    );

    blocTest<POBloc, POState>(
      'emits [POAcknowledging, POAcknowledged] on AcknowledgePO',
      build: () {
        final ackPO = makePurchaseOrder(status: 'ACKNOWLEDGED');
        when(() => mockRepo.acknowledge(any(), any()))
            .thenAnswer((_) async => ackPO);
        return POBloc(repo: mockRepo);
      },
      seed: () => PODetailLoaded(makePurchaseOrder()),
      act: (bloc) => bloc.add(AcknowledgePO('po-001', '2026-04-01')),
      expect: () => [
        isA<POAcknowledging>(),
        isA<POAcknowledged>()
            .having((s) => s.po.status, 'status', 'ACKNOWLEDGED'),
      ],
    );

    blocTest<POBloc, POState>(
      'emits [POAcknowledging, POError] when acknowledge fails',
      build: () {
        when(() => mockRepo.acknowledge(any(), any()))
            .thenThrow(Exception('Server error'));
        return POBloc(repo: mockRepo);
      },
      seed: () => PODetailLoaded(makePurchaseOrder()),
      act: (bloc) => bloc.add(AcknowledgePO('po-001', '2026-04-01')),
      expect: () => [
        isA<POAcknowledging>(),
        isA<POError>(),
      ],
    );

    blocTest<POBloc, POState>(
      'emits [POLoading, POError] when LoadPOs fails',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: any(named: 'page')))
            .thenThrow(Exception('Network error'));
        return POBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadPOs()),
      expect: () => [
        isA<POLoading>(),
        isA<POError>(),
      ],
    );
  });
}
