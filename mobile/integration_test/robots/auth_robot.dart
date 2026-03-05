import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class AuthRobot {
  final WidgetTester tester;

  AuthRobot(this.tester);

  // Finders
  final emailField = find.byKey(const Key('login_email_input'));
  final passwordField = find.byKey(const Key('login_password_input'));
  final loginButton = find.byKey(const Key('login_submit_button'));
  final errorMessage = find.byKey(const Key('login_error_message'));

  Future<void> enterEmail(String email) async {
    await tester.pumpAndSettle(const Duration(seconds: 5));
    expect(emailField, findsOneWidget);
    await tester.enterText(emailField, email);
    await tester.pump();
  }

  Future<void> enterPassword(String password) async {
    expect(passwordField, findsOneWidget);
    await tester.enterText(passwordField, password);
    await tester.pump();
  }

  Future<void> tapLogin() async {
    expect(loginButton, findsOneWidget);
    await tester.ensureVisible(loginButton);
    await tester.tap(loginButton);
    await tester.pumpAndSettle(const Duration(seconds: 5));
  }

  Future<void> verifyErrorDisplayed(String text) async {
    await tester.pumpAndSettle(const Duration(seconds: 5));
    expect(find.text(text), findsOneWidget);
  }

  Future<void> verifyLoginScreenVisible() async {
    await tester.pumpAndSettle(const Duration(seconds: 5));
    expect(emailField, findsOneWidget);
    expect(passwordField, findsOneWidget);
    expect(loginButton, findsOneWidget);
  }

  Future<void> login(String email, String password) async {
    await enterEmail(email);
    await enterPassword(password);
    await tapLogin();
  }
}
