import 'package:cricnetra/core/api/api_exception.dart';
import 'package:cricnetra/core/theme/app_palette.dart';
import 'package:cricnetra/core/theme/app_theme.dart';
import 'package:cricnetra/features/leaderboards/leaderboards_screen.dart';
import 'package:cricnetra/features/matches/match_screen.dart';
import 'package:cricnetra/features/players/career_screen.dart';
import 'package:cricnetra/features/players/player_screen.dart';
import 'package:cricnetra/features/teams/team_screen.dart';
import 'package:cricnetra/features/tournaments/tournament_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_api.dart';

/// A failing screen must stay escapable.
///
/// Riverpod's `AsyncValue.value` RETHROWS when the provider failed with no
/// prior data, so reading it in a screen's own `build` — an AppBar title, say —
/// throws during build. Flutter then replaces the entire Scaffold, back arrow
/// included, with an ErrorWidget, and the person is stuck on a red box. Any
/// 404 does it: open a shared link to a match that has since been deleted.
///
/// These screens must use `valueOrNull` and render their error INSIDE the
/// Scaffold, so the app bar survives.
void main() {
  /// Pumps [screen] with every API call failing, as a pushed route so there is
  /// a back arrow to look for.
  Future<void> pumpFailing(WidgetTester tester, Widget screen) async {
    final api = FakeApi()..failWith = const ApiException(message: 'player not found', statusCode: 404);

    await tester.pumpWidget(
      ProviderScope(
        overrides: signedInOverrides(api),
        child: MaterialApp(
          theme: AppTheme.from(AppPalette.emerald),
          home: Builder(
            builder: (context) => Scaffold(
              body: Center(
                child: ElevatedButton(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(builder: (_) => screen),
                  ),
                  child: const Text('open'),
                ),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
  }

  /// The screen is escapable if a back button survived the failure.
  void expectEscapable(WidgetTester tester, String what) {
    expect(
      find.byType(BackButton),
      findsOneWidget,
      reason: '$what left the reader with no way back',
    );
    expect(
      find.byType(ErrorWidget),
      findsNothing,
      reason: '$what replaced the whole screen with an error box',
    );
  }

  testWidgets('a match that cannot be loaded keeps its back arrow',
      (tester) async {
    await pumpFailing(tester, const MatchScreen(matchId: '999'));
    expectEscapable(tester, 'MatchScreen');
  });

  testWidgets('a player that cannot be loaded keeps its back arrow',
      (tester) async {
    await pumpFailing(tester, const PlayerScreen(playerId: '999'));
    expectEscapable(tester, 'PlayerScreen');
  });

  testWidgets('a career that cannot be loaded keeps its back arrow',
      (tester) async {
    await pumpFailing(tester, const CareerScreen(playerId: '999'));
    expectEscapable(tester, 'CareerScreen');
  });

  testWidgets('a team that cannot be loaded keeps its back arrow',
      (tester) async {
    await pumpFailing(tester, const TeamScreen(teamId: '999'));
    expectEscapable(tester, 'TeamScreen');
  });

  testWidgets('a tournament that cannot be loaded keeps its back arrow',
      (tester) async {
    await pumpFailing(tester, const TournamentScreen(tournamentId: '999'));
    expectEscapable(tester, 'TournamentScreen');
  });

  testWidgets('leaderboards that cannot be loaded keep their back arrow',
      (tester) async {
    // This is the one a walk actually hit: it needs no id, so More →
    // Leaderboards reaches it with nothing but a dead connection.
    await pumpFailing(tester, const LeaderboardsScreen());
    expectEscapable(tester, 'LeaderboardsScreen');
  });

  testWidgets('the failure is explained, not just survived', (tester) async {
    await pumpFailing(tester, const PlayerScreen(playerId: '999'));

    // A back arrow with a blank page is escapable but unhelpful; the reader
    // should be told what went wrong and offered a retry.
    expect(find.textContaining('not found'), findsWidgets);
    expect(find.text('Try again'), findsOneWidget);
  });
}
