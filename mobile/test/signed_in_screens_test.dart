import 'package:cricnetra/core/models/match.dart';
import 'package:cricnetra/core/models/rules.dart';
import 'package:cricnetra/core/theme/app_palette.dart';
import 'package:cricnetra/core/theme/app_theme.dart';
import 'package:cricnetra/features/matches/widgets/scoreboard.dart';
import 'package:cricnetra/features/matches/widgets/scoring_pad.dart';
import 'package:cricnetra/features/matches/widgets/scorecard.dart';
import 'package:cricnetra/features/matches/widgets/match_charts.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_api.dart';

/// These cover the half of the app that only exists once you are signed in:
/// the scoring surface and the cards a scorer reads between deliveries.
///
/// They render against the real fixture shapes the server sends, so a screen
/// that passes here is wired correctly, not just free of syntax errors.
void main() {
  Widget host(Widget child, {Size size = const Size(375, 812)}) {
    return ProviderScope(
      overrides: signedInOverrides(FakeApi()),
      child: MaterialApp(
        theme: AppTheme.from(AppPalette.emerald),
        home: MediaQuery(
          data: MediaQueryData(size: size),
          child: Scaffold(
            body: SingleChildScrollView(child: child),
          ),
        ),
      ),
    );
  }

  final match = FakeApi.liveMatch;
  final innings = match.current!;

  group('Scoreboard', () {
    testWidgets('shows the score, rate and this over', (tester) async {
      await tester.pumpWidget(host(Scoreboard(match: match, innings: innings)));
      await tester.pump();

      expect(find.text('24/1'), findsOneWidget);
      expect(find.text('2.0 / 20 ov'), findsOneWidget);
      expect(find.text('12.00'), findsOneWidget, reason: 'run rate');
      expect(find.text('LIVE'), findsOneWidget);
      // Every ball of the over should be on screen.
      for (final token in innings.thisOver) {
        expect(find.text(token), findsWidgets, reason: 'ball chip $token');
      }
      expect(tester.takeException(), isNull);
    });

    testWidgets('shows the powerplay and its fielding limit', (tester) async {
      await tester.pumpWidget(host(Scoreboard(match: match, innings: innings)));
      await tester.pump();

      expect(find.text('Powerplay · 2 out'), findsOneWidget);
    });

    testWidgets('shows the chase line while chasing', (tester) async {
      final chasing = Innings.fromJson({
        'batting_team': 'Chennai Kings',
        'bowling_team': 'Mumbai Strikers',
        'runs': 100,
        'wickets': 3,
        'overs_str': '12.0',
        'max_overs': 20,
        'max_wickets': 10,
        'run_rate': 8.33,
        'target': 150,
        'required_runs': 50,
        'balls_remaining': 48,
        'required_run_rate': 6.25,
      });

      await tester.pumpWidget(host(Scoreboard(match: match, innings: chasing)));
      await tester.pump();

      expect(find.text('Need 50 off 48 balls'), findsOneWidget);
      expect(find.text('150'), findsOneWidget, reason: 'target');
      expect(find.text('6.25'), findsOneWidget, reason: 'required rate');
    });
  });

  group('CreaseCard', () {
    testWidgets('shows both batters, the bowler and the stand', (tester) async {
      await tester.pumpWidget(host(CreaseCard(innings: innings)));
      await tester.pump();

      expect(find.text('Virat Kohli'), findsOneWidget);
      expect(find.text('KL Rahul'), findsOneWidget);
      expect(find.text('Arshdeep Singh'), findsOneWidget);
      expect(find.text('8 (4)'), findsOneWidget);
      expect(find.text('Partnership 4 (3)'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  group('ScoringPad', () {
    Widget pad(MatchState m, {List<BallRequest>? sent, List<String>? bowlers}) {
      return host(
        ScoringPad(
          match: m,
          innings: m.current!,
          onBall: (b) async => sent?.add(b),
          onSetBowler: (b) async => bowlers?.add(b),
          onUndo: () async {},
        ),
      );
    }

    testWidgets('offers every key a T20 scorer needs', (tester) async {
      await tester.pumpWidget(pad(match));
      await tester.pump();

      for (final label in ['0', '1', '2', '3', '4', '6', 'OUT', 'Wd', 'Nb',
        'B', 'Lb', 'Undo']) {
        expect(find.text(label), findsWidgets, reason: 'pad key $label');
      }
      expect(find.textContaining('Bowling: Arshdeep Singh'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('a run button sends the right delivery', (tester) async {
      final sent = <BallRequest>[];
      await tester.pumpWidget(pad(match, sent: sent));
      await tester.pump();

      await tester.tap(find.text('4'));
      await tester.pumpAndSettle();

      expect(sent, hasLength(1));
      expect(sent.single.action, BallRequest.actionRuns);
      expect(sent.single.value, 4);
      // Shot tracking is off by default, so no capture dialog should appear.
      expect(sent.single.wagonX, isNull);
    });

    testWidgets('hides keys the rulebook disables', (tester) async {
      // A gully rulebook: no wides, no byes, no leg byes.
      final gully = MatchState.fromJson({
        ...match.toJsonForTest(),
        'rules': const MatchRules(
          name: 'Gully',
          oversPerInnings: 6,
          wide: WideRules(enabled: false),
          byesAllowed: false,
          legByesAllowed: false,
        ).toJson(),
      });

      await tester.pumpWidget(pad(gully));
      await tester.pump();

      expect(find.text('Wd'), findsNothing);
      expect(find.text('B'), findsNothing);
      expect(find.text('Lb'), findsNothing);
      expect(find.text('Nb'), findsOneWidget, reason: 'no-balls stay enabled');
    });

    testWidgets('a rule-out format swaps the six key for a dismissal',
        (tester) async {
      final ruleOut = MatchState.fromJson({
        ...match.toJsonForTest(),
        'rules': const MatchRules(overBoundaryOut: true).toJson(),
      });

      await tester.pumpWidget(pad(ruleOut));
      await tester.pump();

      expect(find.text('6 = OUT'), findsOneWidget);
      expect(find.text('6'), findsNothing);
    });

    testWidgets('a free hit restores the plain six in a rule-out format',
        (tester) async {
      // Boundary-out is not a legal free-hit dismissal, and the engine drops
      // it silently, so the key has to revert or the six is lost.
      final json = match.toJsonForTest();
      (json['innings'] as List)[0]['free_hit'] = true;
      final freeHit = MatchState.fromJson({
        ...json,
        'rules': const MatchRules(overBoundaryOut: true).toJson(),
      });

      await tester.pumpWidget(pad(freeHit));
      await tester.pump();

      expect(find.text('6 = OUT'), findsNothing);
      expect(find.text('6'), findsOneWidget);
    });

    testWidgets('between overs it asks for a bowler', (tester) async {
      final bowlers = <String>[];
      await tester.pumpWidget(
        pad(FakeApi.awaitingBowler, bowlers: bowlers),
      );
      await tester.pump();

      expect(find.text('New over — pick the bowler'), findsOneWidget);
      await tester.tap(find.text('Start over'));
      await tester.pumpAndSettle();

      expect(bowlers, ['Deepak Chahar'], reason: 'the first eligible bowler');
    });
  });

  group('Wicket dialog', () {
    testWidgets('sends the striker keyword the server validates',
        (tester) async {
      final sent = <BallRequest>[];
      await tester.pumpWidget(host(
        ScoringPad(
          match: match,
          innings: innings,
          onBall: (b) async => sent.add(b),
          onSetBowler: (_) async {},
          onUndo: () async {},
        ),
      ));
      await tester.pump();

      await tester.tap(find.text('OUT'));
      await tester.pumpAndSettle();

      expect(find.text('Wicket'), findsOneWidget);
      expect(find.text('Who is out'), findsOneWidget);

      await tester.tap(find.text('Out').last);
      await tester.pumpAndSettle();

      expect(sent, hasLength(1));
      final ball = sent.single;
      expect(ball.action, BallRequest.actionWicket);
      // The server validates this against ^(striker|non_striker)$.
      expect(ball.batterOut, 'striker');
      expect(ball.dismissal, isNotNull);
      expect(ball.toJson()['batter_out'], 'striker');
      // A bowled ends the ball, so no runs picker and nothing to carry.
      expect(ball.value, 0);
    });

    testWidgets('carries the runs completed on a run out', (tester) async {
      // The batters cross and the second run is a run out: those runs count,
      // and dropping them was losing real scores.
      final sent = <BallRequest>[];
      await tester.pumpWidget(host(
        ScoringPad(
          match: match,
          innings: innings,
          onBall: (b) async => sent.add(b),
          onSetBowler: (_) async {},
          onUndo: () async {},
        ),
      ));
      await tester.pump();

      await tester.tap(find.text('OUT'));
      await tester.pumpAndSettle();

      // No runs picker until a dismissal that leaves the ball live is chosen.
      expect(find.text('Runs completed'), findsNothing);

      await tester.tap(find.byType(DropdownButtonFormField<String>).first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Run out').last);
      await tester.pumpAndSettle();

      expect(find.text('Runs completed'), findsOneWidget);
      await tester.tap(find.widgetWithText(InkWell, '2').last);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Out').last);
      await tester.pumpAndSettle();

      expect(sent, hasLength(1));
      expect(sent.single.dismissal, Dismissals.runOut);
      expect(sent.single.value, 2, reason: 'the completed runs');
    });

    testWidgets('offers no runs picker for a dismissal that ends the ball',
        (tester) async {
      // The engine credits `value` to the striker whatever the dismissal, so
      // offering runs on a caught would silently invent them.
      await tester.pumpWidget(host(
        ScoringPad(
          match: match,
          innings: innings,
          onBall: (_) async {},
          onSetBowler: (_) async {},
          onUndo: () async {},
        ),
      ));
      await tester.pump();

      await tester.tap(find.text('OUT'));
      await tester.pumpAndSettle();

      for (final d in ['Bowled', 'Caught', 'LBW', 'Stumped', 'Retired hurt']) {
        await tester.tap(find.byType(DropdownButtonFormField<String>).first);
        await tester.pumpAndSettle();
        await tester.tap(find.text(d).last);
        await tester.pumpAndSettle();
        expect(find.text('Runs completed'), findsNothing, reason: d);
      }
    });

    testWidgets('a free hit limits the dismissals on offer', (tester) async {
      final json = match.toJsonForTest();
      (json['innings'] as List)[0]['free_hit'] = true;
      final freeHit = MatchState.fromJson(json);

      await tester.pumpWidget(host(
        ScoringPad(
          match: freeHit,
          innings: freeHit.current!,
          onBall: (_) async {},
          onSetBowler: (_) async {},
          onUndo: () async {},
        ),
      ));
      await tester.pump();

      await tester.tap(find.text('OUT'));
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Free hit'),
        findsOneWidget,
        reason: 'the scorer should be told why the list is short',
      );
    });
  });

  group('Scorecard', () {
    testWidgets('renders batting, bowling, extras and partnerships',
        (tester) async {
      await tester.pumpWidget(host(InningsScorecard(innings: innings)));
      await tester.pump();

      expect(find.text('Mumbai Strikers batting'), findsOneWidget);
      expect(find.text('Chennai Kings bowling'), findsOneWidget);
      expect(find.text('Rohit Sharma'), findsWidgets);
      expect(find.text('b Arshdeep Singh'), findsOneWidget);
      expect(find.text('not out'), findsWidgets);
      expect(find.text('Extras'), findsOneWidget);
      expect(find.text('Fall of wickets'), findsOneWidget);
      expect(find.text('Partnerships'), findsOneWidget);
      expect(find.text('Best'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('an innings with nobody out still renders', (tester) async {
      final fresh = Innings.fromJson({
        'batting_team': 'A',
        'bowling_team': 'B',
        'max_overs': 20,
        'max_wickets': 10,
      });

      await tester.pumpWidget(host(InningsScorecard(innings: fresh)));
      await tester.pump();

      expect(find.text('Yet to bat'), findsOneWidget);
      expect(find.text('No overs bowled yet'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  group('Charts', () {
    testWidgets('the wagon wheel plots the recorded shots', (tester) async {
      await tester.pumpWidget(host(WagonWheel(shots: innings.wagon)));
      await tester.pump();

      expect(find.text('Four'), findsOneWidget);
      expect(find.text('Six'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('an untracked innings explains itself', (tester) async {
      await tester.pumpWidget(host(const WagonWheel(shots: [])));
      await tester.pump();

      expect(find.text('No shot directions recorded'), findsOneWidget);
      expect(find.textContaining('Turn on Shots'), findsOneWidget);
    });

    testWidgets('the pitch map explains itself when empty', (tester) async {
      await tester.pumpWidget(host(const PitchMap(marks: [])));
      await tester.pump();

      expect(find.text('No pitch data recorded'), findsOneWidget);
    });
  });

  group('Awards', () {
    testWidgets('renders once the match has a result', (tester) async {
      final awards = MatchAwards.fromJson({
        'man_of_the_match': {'name': 'Virat Kohli', 'line': '82 (45)'},
        'best_bowler': {'name': 'Arshdeep Singh', 'line': '3/24'},
      });

      await tester.pumpWidget(host(AwardsCard(awards: awards)));
      await tester.pump();

      expect(find.text('Virat Kohli'), findsOneWidget);
      expect(find.textContaining('Player of the Match'), findsOneWidget);
      expect(find.textContaining('3/24'), findsOneWidget);
    });

    testWidgets('renders nothing while the match is live', (tester) async {
      await tester.pumpWidget(host(const AwardsCard(awards: MatchAwards())));
      await tester.pump();

      expect(find.text('Awards'), findsNothing);
    });
  });
}
