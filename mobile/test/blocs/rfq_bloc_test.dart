import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/presentation/rfqs/bloc/rfq_bloc.dart';

import '../helpers/mocks.dart';
import '../helpers/fixtures.dart';

void main() {
  late MockRFQRepository mockRepo;

  setUp(() {
    mockRepo = MockRFQRepository();
  });

  group('RFQBloc', () {
    blocTest<RFQBloc, RFQState>(
      'emits [RFQLoading, RFQListLoaded] on LoadRFQs',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: any(named: 'page')))
            .thenAnswer((_) async => [makeRFQ()]);
        return RFQBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadRFQs()),
      expect: () => [
        isA<RFQLoading>(),
        isA<RFQListLoaded>()
            .having((s) => s.rfqs.length, 'count', 1)
            .having((s) => s.hasMore, 'hasMore', false),
      ],
    );

    blocTest<RFQBloc, RFQState>(
      'emits [RFQLoading, RFQListLoaded] with activeStatus on filtered load',
      build: () {
        when(() => mockRepo.list(status: 'OPEN', page: 1))
            .thenAnswer((_) async => [makeRFQ(status: 'OPEN')]);
        return RFQBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadRFQs(status: 'OPEN')),
      expect: () => [
        isA<RFQLoading>(),
        isA<RFQListLoaded>()
            .having((s) => s.activeStatus, 'activeStatus', 'OPEN'),
      ],
    );

    blocTest<RFQBloc, RFQState>(
      'emits [RFQLoading, RFQDetailLoaded] on LoadRFQDetail',
      build: () {
        when(() => mockRepo.getById(any()))
            .thenAnswer((_) async => makeRFQ());
        return RFQBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadRFQDetail('rfq-001')),
      expect: () => [
        isA<RFQLoading>(),
        isA<RFQDetailLoaded>(),
      ],
    );

    blocTest<RFQBloc, RFQState>(
      'emits [RFQLoading, BidSubmitted] on successful SubmitBid',
      build: () {
        when(() => mockRepo.submitBid(
              any(),
              unitPriceCents: any(named: 'unitPriceCents'),
              leadTimeDays: any(named: 'leadTimeDays'),
              comments: any(named: 'comments'),
            )).thenAnswer((_) async {});
        return RFQBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(SubmitBid(
        rfqId: 'rfq-001',
        unitPriceCents: 50000,
        leadTimeDays: 14,
      )),
      expect: () => [
        isA<RFQLoading>(),
        isA<BidSubmitted>(),
      ],
    );

    blocTest<RFQBloc, RFQState>(
      'emits [RFQLoading, RFQError] when SubmitBid fails',
      build: () {
        when(() => mockRepo.submitBid(
              any(),
              unitPriceCents: any(named: 'unitPriceCents'),
              leadTimeDays: any(named: 'leadTimeDays'),
              comments: any(named: 'comments'),
            )).thenThrow(Exception('Bid rejected'));
        return RFQBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(SubmitBid(
        rfqId: 'rfq-001',
        unitPriceCents: 50000,
        leadTimeDays: 14,
      )),
      expect: () => [
        isA<RFQLoading>(),
        isA<RFQError>(),
      ],
    );

    blocTest<RFQBloc, RFQState>(
      'LoadMoreRFQs appends and increments page',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 2))
            .thenAnswer((_) async => [makeRFQ(id: 'rfq-new')]);
        return RFQBloc(repo: mockRepo);
      },
      seed: () => RFQListLoaded(
        [makeRFQ()],
        hasMore: true,
        page: 1,
      ),
      act: (bloc) => bloc.add(LoadMoreRFQs()),
      expect: () => [
        isA<RFQListLoaded>().having((s) => s.isLoadingMore, 'loading', true),
        isA<RFQListLoaded>()
            .having((s) => s.rfqs.length, 'count', 2)
            .having((s) => s.page, 'page', 2),
      ],
    );

    blocTest<RFQBloc, RFQState>(
      'emits [RFQLoading, RFQError] when LoadRFQs fails',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: any(named: 'page')))
            .thenThrow(Exception('Network error'));
        return RFQBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadRFQs()),
      expect: () => [
        isA<RFQLoading>(),
        isA<RFQError>(),
      ],
    );

    blocTest<RFQBloc, RFQState>(
      'RefreshRFQs emits RFQListLoaded',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 1))
            .thenAnswer((_) async => [makeRFQ()]);
        return RFQBloc(repo: mockRepo);
      },
      seed: () => RFQListLoaded([makeRFQ()], hasMore: false, page: 1),
      act: (bloc) => bloc.add(RefreshRFQs()),
      expect: () => [isA<RFQListLoaded>()],
    );

    blocTest<RFQBloc, RFQState>(
      'RefreshRFQs emits RFQError on failure',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 1))
            .thenThrow(Exception('Timeout'));
        return RFQBloc(repo: mockRepo);
      },
      seed: () => RFQListLoaded([makeRFQ()], hasMore: false, page: 1),
      act: (bloc) => bloc.add(RefreshRFQs()),
      expect: () => [isA<RFQError>()],
    );

    blocTest<RFQBloc, RFQState>(
      'LoadMoreRFQs does nothing when hasMore is false',
      build: () => RFQBloc(repo: mockRepo),
      seed: () => RFQListLoaded([makeRFQ()], hasMore: false, page: 1),
      act: (bloc) => bloc.add(LoadMoreRFQs()),
      expect: () => [],
    );

    blocTest<RFQBloc, RFQState>(
      'LoadMoreRFQs recovers on error',
      build: () {
        when(() => mockRepo.list(status: any(named: 'status'), page: 2))
            .thenThrow(Exception('Network error'));
        return RFQBloc(repo: mockRepo);
      },
      seed: () => RFQListLoaded([makeRFQ()], hasMore: true, page: 1),
      act: (bloc) => bloc.add(LoadMoreRFQs()),
      expect: () => [
        isA<RFQListLoaded>().having((s) => s.isLoadingMore, 'loading', true),
        isA<RFQListLoaded>()
            .having((s) => s.rfqs.length, 'count', 1)
            .having((s) => s.page, 'page', 1),
      ],
    );

    blocTest<RFQBloc, RFQState>(
      'LoadRFQDetail emits RFQError on failure',
      build: () {
        when(() => mockRepo.getById(any()))
            .thenThrow(Exception('Not found'));
        return RFQBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadRFQDetail('rfq-999')),
      expect: () => [
        isA<RFQLoading>(),
        isA<RFQError>(),
      ],
    );
  });
}
