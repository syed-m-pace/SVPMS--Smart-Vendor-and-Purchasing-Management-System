import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_test/flutter_test.dart';

class AuthRobot {
  final WidgetTester tester;

  AuthRobot(this.tester);

  // Finders
  final emailField = find.byKey(const Key('login_email_input'));
  final passwordField = find.byKey(const Key('login_password_input'));
  final loginButton = find.byKey(const Key('login_submit_button'));
  final errorMessage = find.byKey(const Key('login_error_message'));

  Future<void> waitFor(
    Finder finder, {
    Duration timeout = const Duration(seconds: 10),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      if (finder.evaluate().isNotEmpty) return;
      await tester.pump(const Duration(milliseconds: 100));
    }
    throw TimeoutException('Timed out waiting for $finder');
  }

  Future<void> enterEmail(String email) async {
    await waitFor(emailField);
    await tester.enterText(emailField, email);
    await tester.pump();
  }

  Future<void> enterPassword(String password) async {
    await waitFor(passwordField);
    await tester.enterText(passwordField, password);
    await tester.pump();
  }

  Future<void> tapLogin() async {
    await waitFor(loginButton);
    await tester.ensureVisible(loginButton);
    await tester.tap(loginButton);
    await tester.pumpAndSettle();
  }

  Future<void> verifyErrorDisplayed(String text) async {
    // Error messages might be in SnackBar or Dialog, so we wait for text
    final textFinder = find.text(text);
    await waitFor(textFinder);
    expect(textFinder, findsOneWidget);
  }

  Future<void> login(String email, String password) async {
    await enterEmail(email);
    await enterPassword(password);
    await tapLogin();
  }
}
