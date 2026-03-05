import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mocktail/mocktail.dart';
import 'package:svpms_vendor/presentation/auth/bloc/auth_bloc.dart';
import 'package:svpms_vendor/presentation/auth/screens/login_screen.dart';

import 'helpers/mocks.dart';

void main() {
  late MockAuthRepository mockAuthRepo;
  late AuthBloc authBloc;

  setUpAll(() {
    GoogleFonts.config.allowRuntimeFetching = false;
  });

  setUp(() {
    mockAuthRepo = MockAuthRepository();
    authBloc = AuthBloc(repo: mockAuthRepo);
  });

  tearDown(() async {
    // Bloc.close() hangs if BlocBuilder still has an active subscription.
    // The test framework unmounts widgets after the test body completes,
    // so we just fire-and-forget the close here.
    authBloc.close();
  });

  testWidgets('Login screen renders email, password, and submit button',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: BlocProvider<AuthBloc>.value(
          value: authBloc,
          child: const LoginScreen(),
        ),
      ),
    );
    await tester.pump();

    expect(find.byKey(const Key('login_email_input')), findsOneWidget);
    expect(find.byKey(const Key('login_password_input')), findsOneWidget);
    expect(find.byKey(const Key('login_submit_button')), findsOneWidget);
    expect(find.text('Sign In'), findsWidgets);
  });

  testWidgets('Login button triggers LoginRequested event', (tester) async {
    when(() => mockAuthRepo.login(any(), any()))
        .thenThrow(Exception('Test error'));

    await tester.pumpWidget(
      MaterialApp(
        home: BlocProvider<AuthBloc>.value(
          value: authBloc,
          child: const LoginScreen(),
        ),
      ),
    );
    await tester.pump();

    await tester.enterText(
        find.byKey(const Key('login_email_input')), 'test@test.com');
    await tester.enterText(
        find.byKey(const Key('login_password_input')), 'password');
    await tester.tap(find.byKey(const Key('login_submit_button')));
    await tester.pump();
    await tester.pump();

    verify(() => mockAuthRepo.login('test@test.com', 'password')).called(1);
  });
}
