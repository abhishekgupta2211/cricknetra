import 'package:cricnetra/core/models/match.dart';
import 'package:flutter_test/flutter_test.dart';

/// The fielder dropdown feeds catches, stumpings and run-outs, which feed the
/// fielding statistics and the "most catches" board. It has to list the side
/// that is actually in the field and nobody else.
void main() {
  MatchState buildMatch({
    List<String> availableBowlers = const [],
    List<Map<String, dynamic>> innings = const [],
    int currentInnings = 1,
  }) {
    return MatchState.fromJson({
      'id': '1',
      'team_a': 'Mumbai',
      'team_b': 'Chennai',
      'current_innings': currentInnings,
      'available_bowlers': availableBowlers,
      'innings': innings,
    });
  }

  test('keeps a bowler who has finished his quota', () {
    // The server prunes available_bowlers to who may bowl NEXT, so a bowler
    // who has bowled out disappears from it while still on the field.
    final match = buildMatch(
      availableBowlers: ['Arshdeep Singh'],
      innings: [
        {
          'batting_team': 'Mumbai',
          'bowling_team': 'Chennai',
          'bowlers': [
            {'name': 'Deepak Chahar', 'overs': '4.0'},
            {'name': 'Arshdeep Singh', 'overs': '2.0'},
          ],
        }
      ],
    );

    final names = fieldingSideNames(match);

    expect(names, contains('Deepak Chahar'));
    expect(names, contains('Arshdeep Singh'));
  });

  test('never offers the batting side as fielders', () {
    // Chennai are bowling, so no Mumbai batter may be credited with a catch,
    // dismissed or not.
    final match = buildMatch(
      availableBowlers: ['Arshdeep Singh'],
      innings: [
        {
          'batting_team': 'Mumbai',
          'bowling_team': 'Chennai',
          'batters': [
            {'name': 'Rohit Sharma', 'has_batted': true, 'out': true},
            {'name': 'Virat Kohli', 'has_batted': true},
            {'name': 'KL Rahul', 'has_batted': true},
          ],
          'bowlers': [
            {'name': 'Arshdeep Singh'},
          ],
          'striker': 'Virat Kohli',
          'non_striker': 'KL Rahul',
        }
      ],
    );

    final names = fieldingSideNames(match);

    expect(names, ['Arshdeep Singh']);
    expect(names, isNot(contains('Rohit Sharma')));
    expect(names, isNot(contains('Virat Kohli')));
  });

  test('in the second innings it follows the sides swapping over', () {
    // Mumbai bowled the first innings and bat the second, so Chennai are now
    // fielding: their bowler plus the men who batted for them earlier.
    final match = buildMatch(
      currentInnings: 2,
      availableBowlers: ['Deepak Chahar'],
      innings: [
        {
          'batting_team': 'Chennai',
          'bowling_team': 'Mumbai',
          'batters': [
            {'name': 'Ruturaj', 'has_batted': true},
          ],
          'bowlers': [
            {'name': 'Jasprit Bumrah'},
          ],
        },
        {
          'batting_team': 'Mumbai',
          'bowling_team': 'Chennai',
          'batters': [
            {'name': 'Rohit Sharma', 'has_batted': true},
          ],
          'bowlers': [
            {'name': 'Deepak Chahar'},
          ],
        }
      ],
    );

    // Innings 2: Mumbai batting, Chennai fielding.
    final names = fieldingSideNames(match);

    expect(names, contains('Deepak Chahar'), reason: 'bowling now');
    expect(names, isNot(contains('Jasprit Bumrah')),
        reason: 'Mumbai bowler, and Mumbai are batting');
    expect(names, contains('Ruturaj'), reason: 'batted for Chennai earlier');
    expect(names, isNot(contains('Rohit Sharma')), reason: 'batting now');
  });

  test('is never empty in a live match', () {
    // The engine falls back to the whole bowling order, so there is always
    // somebody to pick.
    final match = buildMatch(
      availableBowlers: ['A', 'B'],
      innings: [
        {'batting_team': 'Mumbai', 'bowling_team': 'Chennai'},
      ],
    );

    expect(fieldingSideNames(match), isNotEmpty);
  });

  test('copes with a match that has no innings yet', () {
    expect(fieldingSideNames(MatchState.fromJson({'id': '1'})), isEmpty);
  });
}
