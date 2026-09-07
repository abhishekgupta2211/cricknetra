import 'package:cricnetra/core/models/match.dart';
import 'package:cricnetra/core/models/rules.dart';
import 'package:cricnetra/core/utils/formatters.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('MatchRules', () {
    test('round-trips every field the engine cares about', () {
      // A rulebook edited in the builder must survive the trip to the server
      // and back without losing settings the engine reads.
      const original = MatchRules(
        name: 'Society box',
        formatId: 'custom',
        playersPerSide: 8,
        oversPerInnings: 6,
        ballsPerOver: 5,
        ballType: BallTypes.tennis,
        maxOversPerBowler: 2,
        lastManStands: true,
        overBoundaryOut: true,
        superOverOnTie: true,
        dlsEnabled: true,
        allowDeclaration: true,
        defaultFieldersOutside: 3,
        powerplays: [
          PowerplayRange(startOver: 1, endOver: 2, maxFieldersOutside: 1),
        ],
        wide: WideRules(runPenalty: 2, countsAsLegalBall: true),
        noBall: NoBallRules(freeHit: false, offBatCounts: false),
        byesAllowed: false,
        legByesAllowed: false,
        allowedDismissals: [Dismissals.bowled, Dismissals.caught],
        fourValue: 3,
        sixValue: 5,
      );

      final restored = MatchRules.fromJson(original.toJson());

      expect(restored.name, 'Society box');
      expect(restored.playersPerSide, 8);
      expect(restored.oversPerInnings, 6);
      expect(restored.ballsPerOver, 5);
      expect(restored.ballType, BallTypes.tennis);
      expect(restored.maxOversPerBowler, 2);
      expect(restored.lastManStands, isTrue);
      expect(restored.overBoundaryOut, isTrue);
      expect(restored.superOverOnTie, isTrue);
      expect(restored.dlsEnabled, isTrue);
      expect(restored.allowDeclaration, isTrue);
      expect(restored.defaultFieldersOutside, 3);
      expect(restored.powerplays.single.maxFieldersOutside, 1);
      expect(restored.wide.runPenalty, 2);
      expect(restored.wide.countsAsLegalBall, isTrue);
      expect(restored.noBall.freeHit, isFalse);
      expect(restored.noBall.offBatCounts, isFalse);
      expect(restored.byesAllowed, isFalse);
      expect(restored.legByesAllowed, isFalse);
      expect(restored.allowedDismissals, [Dismissals.bowled, Dismissals.caught]);
      expect(restored.fourValue, 3);
      expect(restored.sixValue, 5);
    });

    test('last man stands changes how many wickets end the innings', () {
      const normal = MatchRules(playersPerSide: 11);
      const lastMan = MatchRules(playersPerSide: 11, lastManStands: true);

      expect(normal.wicketsToAllOut, 10);
      expect(lastMan.wicketsToAllOut, 11);
    });

    test('boundary-out is only selectable in a rule-out format', () {
      const normal = MatchRules();
      const ruleOut = MatchRules(overBoundaryOut: true);

      expect(normal.dismissalAllowed(Dismissals.boundaryOut), isFalse);
      expect(ruleOut.dismissalAllowed(Dismissals.boundaryOut), isTrue);
      expect(
        ruleOut.selectableDismissals.contains(Dismissals.boundaryOut),
        isTrue,
      );
    });
  });

  group('BallRequest', () {
    test('sends the literal striker keyword, not a player name', () {
      // The server validates batter_out against ^(striker|non_striker)$, so a
      // name here is a guaranteed rejection.
      const ball = BallRequest(
        action: BallRequest.actionWicket,
        dismissal: Dismissals.bowled,
        batterOut: 'non_striker',
      );

      expect(ball.toJson()['batter_out'], 'non_striker');
      expect(ball.toJson()['dismissal'], 'bowled');
    });

    test('omits capture fields that were never recorded', () {
      const ball = BallRequest(action: BallRequest.actionRuns, value: 4);
      final json = ball.toJson();

      expect(json.containsKey('wagon_x'), isFalse);
      expect(json.containsKey('pitch_x'), isFalse);
      expect(json.containsKey('fielder'), isFalse);
    });

    test('knows which deliveries came off the bat', () {
      expect(
        const BallRequest(action: BallRequest.actionRuns, value: 4).isBatShot,
        isTrue,
      );
      expect(
        const BallRequest(action: BallRequest.actionRuns).isBatShot,
        isFalse,
      );
      expect(
        const BallRequest(action: BallRequest.actionWide, value: 1).isBatShot,
        isFalse,
      );
      expect(
        const BallRequest(
          action: BallRequest.actionWicket,
          dismissal: Dismissals.caught,
        ).isBatShot,
        isTrue,
      );
    });
  });

  group('MatchState parsing', () {
    test('reads a live innings from the shape the server actually sends', () {
      final state = MatchState.fromJson({
        'id': '2',
        'team_a': 'Mumbai Strikers',
        'team_b': 'Chennai Kings',
        'bat_first': 'Mumbai Strikers',
        'rules_name': 'T20',
        'current_innings': 1,
        'over_pending': true,
        'available_bowlers': ['Deepak Chahar'],
        'innings': [
          {
            'batting_team': 'Mumbai Strikers',
            'bowling_team': 'Chennai Kings',
            'runs': 13,
            'wickets': 1,
            'overs_str': '1.0',
            'max_overs': 20,
            'max_wickets': 10,
            'extras': {'wides': 1, 'total': 2},
            'run_rate': 13.0,
            'this_over': ['4', '1', 'Wd', '6', '1L', '•', 'W'],
            'manhattan': [13],
            'batters': [
              {'name': 'Rohit Sharma', 'runs': 5, 'balls': 4, 'has_batted': true},
            ],
            'partnerships': [
              {'wicket': 1, 'runs': 13, 'balls': 6, 'unbroken': false},
            ],
          }
        ],
      });

      expect(state.title, 'Mumbai Strikers v Chennai Kings');
      expect(state.isLive, isTrue);
      expect(state.overPending, isTrue);
      expect(state.current?.scoreLine, '13/1');
      expect(state.current?.thisOver.length, 7);
      expect(state.current?.extras.total, 2);
      expect(state.current?.wicketsLeft, 9);
      expect(state.current?.whoBatted.single.figure, '5 (4)');
    });

    test('survives a payload with missing and null fields', () {
      final state = MatchState.fromJson({'id': '1'});

      expect(state.innings, isEmpty);
      expect(state.current, isNull);
      expect(state.awards, isNull);
      expect(state.dls, isNull);
      expect(state.meta.isEmpty, isTrue);
    });
  });

  group('Fmt', () {
    test('reads overs as overs.balls, not as a decimal', () {
      // 12.3 means twelve overs and three balls, which is 12.5 in decimal.
      expect(Fmt.oversToDecimal(12.3), closeTo(12.5, 0.001));
      expect(Fmt.oversToBalls(12.3), 75);
      // A sixth ball rolls over into the next over.
      expect(Fmt.oversToDecimal(1.6), 2);
    });

    test('turns a ball count back into an over string', () {
      expect(Fmt.ballsToOvers(75), '12.3');
      expect(Fmt.ballsToOvers(0), '0.0');
    });

    test('builds initials from a name', () {
      expect(Fmt.initials('Rohit Sharma'), 'RS');
      expect(Fmt.initials('Rohit'), 'RO');
      expect(Fmt.initials(''), '?');
    });

    test('signs a net run rate', () {
      expect(Fmt.signed(0.5), '+0.500');
      expect(Fmt.signed(-0.25), '-0.250');
    });
  });
}
