import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/presentation/dashboard/bloc/dashboard_bloc.dart';

import '../helpers/mocks.dart';
import '../helpers/fixtures.dart';

void main() {
  late MockDashboardRepository mockRepo;

  setUp(() {
    mockRepo = MockDashboardRepository();
  });

  group('DashboardBloc', () {
    blocTest<DashboardBloc, DashboardState>(
      'emits [DashboardLoading, DashboardLoaded] on successful load',
      build: () {
        when(() => mockRepo.getStats())
            .thenAnswer((_) async => makeDashboardStats());
        when(() => mockRepo.getRecentPOs())
            .thenAnswer((_) async => [makePurchaseOrder()]);
        return DashboardBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadDashboard()),
      expect: () => [
        isA<DashboardLoading>(),
        isA<DashboardLoaded>()
            .having((s) => s.stats.activePOs, 'activePOs', 5)
            .having((s) => s.recentPOs.length, 'recentPOs', 1),
      ],
    );

    blocTest<DashboardBloc, DashboardState>(
      'emits [DashboardLoading, DashboardError] when getStats throws',
      build: () {
        when(() => mockRepo.getStats())
            .thenThrow(Exception('Network error'));
        when(() => mockRepo.getRecentPOs())
            .thenAnswer((_) async => []);
        return DashboardBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(LoadDashboard()),
      expect: () => [
        isA<DashboardLoading>(),
        isA<DashboardError>(),
      ],
    );

    blocTest<DashboardBloc, DashboardState>(
      'emits [DashboardLoaded] on refresh (no DashboardLoading)',
      build: () {
        when(() => mockRepo.getStats())
            .thenAnswer((_) async => makeDashboardStats(activePOs: 10));
        when(() => mockRepo.getRecentPOs())
            .thenAnswer((_) async => []);
        return DashboardBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(RefreshDashboard()),
      expect: () => [
        isA<DashboardLoaded>()
            .having((s) => s.stats.activePOs, 'activePOs', 10),
      ],
    );

    blocTest<DashboardBloc, DashboardState>(
      'emits [DashboardError] when refresh fails',
      build: () {
        when(() => mockRepo.getStats())
            .thenThrow(Exception('Timeout'));
        when(() => mockRepo.getRecentPOs())
            .thenAnswer((_) async => []);
        return DashboardBloc(repo: mockRepo);
      },
      act: (bloc) => bloc.add(RefreshDashboard()),
      expect: () => [isA<DashboardError>()],
    );
  });
}
