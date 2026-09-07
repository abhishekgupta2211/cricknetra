import 'package:cricnetra/core/models/career.dart';
import 'package:cricnetra/core/models/roster.dart';
import 'package:cricnetra/core/theme/app_palette.dart';
import 'package:cricnetra/core/theme/app_theme.dart';
import 'package:cricnetra/features/players/career_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'support/fake_api.dart';

/// A player's career page: every match they have played and how they went in
/// each competition. The screen has to be honest about the difference between
/// "did not bat" and "scored nothing", and must not count a live match as a
/// loss.
void main() {
  final history = FakeApi.historyFixture;

  Widget host(Widget child) {
    final router = GoRouter(
      routes: [
        GoRoute(path: '/', builder: (context, state) => child),
        GoRoute(
          path: '/matches/:id',
          builder: (context, state) => const Scaffold(body: Text('match')),
        ),
      ],
    );
    return ProviderScope(
      overrides: signedInOverrides(FakeApi()),
      child: MaterialApp.router(
        theme: AppTheme.from(AppPalette.emerald),
        routerConfig: router,
      ),
    );
  }

  group('the career model', () {
    test('picks the best innings and the best spell', () {
      expect(history.bestInnings?.runs, 62);
      expect(history.bestSpell?.wickets, 2);
      expect(history.bestSpell?.bowlLine, '2/12 (2.0)');
    });

    test('knows which competitions a player has appeared in', () {
      expect(history.tournaments, ['Winter Shield', 'City Premier League']);
    });

    test('a live match is live, not a result', () {
      final live = history.matches.first;
      expect(live.isLive, isTrue);
      expect(live.outcomeLabel, 'Live');
      // It must not be counted against the win record.
      expect(history.won + history.lost, 2, reason: '3 played, 1 still live');
    });

    test('reads a fifty and a three-for as standouts', () {
      final fifty = history.matches[1];
      expect(fifty.isMilestoneInnings, isTrue);
      expect(fifty.isStandoutSpell, isFalse, reason: '2 wickets is not a haul');
    });

    test('spells out a fielding contribution in words', () {
      expect(history.matches[2].fieldingLine, '1 catch · 1 run out');
      expect(history.matches[2].tookAFieldingCredit, isTrue);
      expect(history.matches[0].tookAFieldingCredit, isFalse);
    });

    test('a match with no batting keeps its batting fields null', () {
      // Null is not zero: it separates "did not bat" from "out for nought".
      final noBat = CareerMatch.fromJson({
        'match_id': '9',
        'batted': false,
      });
      expect(noBat.runs, isNull);
      expect(noBat.batted, isFalse);

      final duck = CareerMatch.fromJson({
        'match_id': '9',
        'batted': true,
        'runs': 0,
        'balls': 3,
      });
      expect(duck.runs, 0);
      expect(duck.batted, isTrue);
    });

    test('a bucket knows whether it is worth showing', () {
      final batted = history.byTournament.first;
      expect(batted.hasBatting, isTrue);
      expect(batted.hasBowling, isTrue);

      final batOnly = history.byTournament[1];
      expect(batOnly.hasBatting, isTrue);
      expect(batOnly.hasBowling, isFalse, reason: 'never bowled in that cup');
    });
  });

  group('the career screen', () {
    testWidgets('opens on the overview with the career summary',
        (tester) async {
      await tester.pumpWidget(host(const CareerScreen(playerId: '1')));
      await tester.pumpAndSettle();

      expect(find.text('Rohit Sharma'), findsWidgets);
      expect(find.text('3'), findsWidgets, reason: 'matches played');
      expect(find.text('Career best'), findsOneWidget);
      expect(find.text('62* (38)'), findsOneWidget);
      expect(find.text('2/12 (2.0)'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('breaks the record down by tournament', (tester) async {
      await tester.pumpWidget(host(const CareerScreen(playerId: '1')));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cups'));
      await tester.pumpAndSettle();

      expect(find.text('Winter Shield'), findsOneWidget);
      expect(find.text('City Premier League'), findsOneWidget);
      expect(find.text('1 match'), findsWidgets);
      expect(tester.takeException(), isNull);
    });

    testWidgets('lists every match with what the player did', (tester) async {
      await tester.pumpWidget(host(const CareerScreen(playerId: '1')));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Matches'));
      await tester.pumpAndSettle();

      expect(find.text('v Chennai Kings'), findsNWidgets(2));
      expect(find.text('v Delhi Riders'), findsOneWidget);
      expect(find.text('Won'), findsOneWidget);
      expect(find.text('Lost'), findsOneWidget);
      expect(find.text('Live'), findsOneWidget);
      // Each line carries the player's own contribution, not the team score.
      expect(find.text('62* (38)'), findsOneWidget);
      expect(find.text('1/18 (2.0)'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('a player who has never played is told so, not shown zeros',
        (tester) async {
      final api = FakeApi()..historyOverride = const PlayerHistory(
            player: Player(id: '9', name: 'New Signing'),
          );

      await tester.pumpWidget(
        ProviderScope(
          overrides: signedInOverrides(api),
          child: MaterialApp(
            theme: AppTheme.from(AppPalette.emerald),
            home: const CareerScreen(playerId: '9'),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('has not played yet'), findsOneWidget);
      expect(find.text('Career best'), findsNothing);
    });
  });
}
