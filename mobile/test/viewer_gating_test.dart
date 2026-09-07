import 'package:cricnetra/core/auth/auth_provider.dart';
import 'package:cricnetra/core/models/user.dart';
import 'package:cricnetra/core/theme/app_palette.dart';
import 'package:cricnetra/core/theme/app_theme.dart';
import 'package:cricnetra/core/widgets/common.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_api.dart';

/// Somebody signed out — or signed in without the capability — is a viewer.
/// Offering them a control that only leads to a locked screen wastes a tap and
/// makes the app look broken, so the create actions have to be hidden, not
/// merely rejected afterwards.
void main() {
  Widget host(Widget child, {required List<Override> overrides}) {
    return ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        theme: AppTheme.from(AppPalette.emerald),
        home: child,
      ),
    );
  }

  group('capabilities', () {
    test('a guest can do nothing that writes', () {
      const guest = AuthState(status: AuthStatus.signedOut);

      expect(guest.can(Caps.createMatch), isFalse);
      expect(guest.can(Caps.createTeam), isFalse);
      expect(guest.can(Caps.createTournament), isFalse);
      expect(guest.can(Caps.scoreMatch), isFalse);
      expect(guest.isSignedIn, isFalse);
    });

    test('a plain member still cannot start a match', () {
      // The backend grants a general user no write capabilities at all, so the
      // app must not offer the shortcut just because somebody is signed in.
      final member = AuthState(
        status: AuthStatus.signedIn,
        user: AppUser.fromJson({
          'id': '9',
          'full_name': 'Plain Member',
          'username': 'member',
          'role': 'general_user',
          'capabilities': const <String>[],
        }),
      );

      expect(member.isSignedIn, isTrue);
      expect(member.can(Caps.createMatch), isFalse);
      expect(member.can(Caps.createTeam), isFalse);
    });

    test('the seeded admin can do all of it', () {
      final admin = AuthState(
        status: AuthStatus.signedIn,
        user: FakeApi.adminUser,
      );

      expect(admin.can(Caps.createMatch), isTrue);
      expect(admin.can(Caps.createTeam), isTrue);
      expect(admin.can(Caps.createTournament), isTrue);
      expect(admin.can(Caps.scoreMatch), isTrue);
      expect(admin.isAdmin, isTrue);
    });
  });

  group('GateCard', () {
    testWidgets('asks a guest to sign in', (tester) async {
      var signIn = 0;
      var register = 0;

      await tester.pumpWidget(host(
        Scaffold(
          body: GateCard(
            what: 'score a match',
            signedIn: false,
            onSignIn: () => signIn++,
            onRegister: () => register++,
          ),
        ),
        overrides: signedOutOverrides(FakeApi()),
      ));
      await tester.pump();

      expect(find.textContaining('score a match'), findsOneWidget);
      expect(find.text('Sign in'), findsOneWidget);
      expect(find.text('Create account'), findsOneWidget);

      await tester.tap(find.text('Sign in'));
      await tester.pump();
      expect(signIn, 1);
      expect(register, 0);
    });

    testWidgets('tells a signed-in member it is their role, not the sign-in',
        (tester) async {
      await tester.pumpWidget(host(
        const Scaffold(
          body: GateCard(
            what: 'score a match',
            signedIn: true,
            role: 'general_user',
          ),
        ),
        overrides: signedOutOverrides(FakeApi()),
      ));
      await tester.pump();

      // Asking somebody who is already signed in to sign in again is the
      // frustrating version of this screen.
      expect(find.text('Sign in'), findsNothing);
      expect(find.textContaining('general user'), findsOneWidget);
    });
  });
}
