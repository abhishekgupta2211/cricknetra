/// A player's full career record, from `GET /players/{id}/history`.
///
/// `PlayerStats.recent` is a five-game sample for the form card. This is the
/// other question: everything they have ever played, match by match, and how
/// they went in each competition.
library;

import 'json.dart';
import 'roster.dart';

/// One match in a player's career, with everything they did in it.
class CareerMatch {
  final String matchId;

  /// ISO timestamp the match was created; null on a record with no date.
  final String? playedOn;
  final String format;
  final String team;
  final String opponent;
  final String? tournament;
  final String? venue;
  final String? matchNo;

  final String? result;

  /// won · lost · tied · no_result · in_progress, from THIS player's side.
  final String outcome;

  // Batting. Everything is null when they did not bat, so a duck reads
  // differently from never having gone in.
  final bool batted;
  final int? runs;
  final int? balls;
  final int fours;
  final int sixes;
  final double? strikeRate;
  final bool notOut;
  final String? howOut;
  final String? dismissalText;
  final String? batLine;

  final bool bowled;
  final String? overs;
  final int maidens;
  final int? runsConceded;
  final int? wickets;
  final double? economy;
  final String? bowlLine;

  final int catches;
  final int runOuts;
  final int stumpings;

  const CareerMatch({
    required this.matchId,
    this.playedOn,
    this.format = '',
    this.team = '',
    this.opponent = '',
    this.tournament,
    this.venue,
    this.matchNo,
    this.result,
    this.outcome = 'in_progress',
    this.batted = false,
    this.runs,
    this.balls,
    this.fours = 0,
    this.sixes = 0,
    this.strikeRate,
    this.notOut = false,
    this.howOut,
    this.dismissalText,
    this.batLine,
    this.bowled = false,
    this.overs,
    this.maidens = 0,
    this.runsConceded,
    this.wickets,
    this.economy,
    this.bowlLine,
    this.catches = 0,
    this.runOuts = 0,
    this.stumpings = 0,
  });

  factory CareerMatch.fromJson(Map<String, dynamic> j) => CareerMatch(
        matchId: asStr(j['match_id']),
        playedOn: asStrOrNull(j['played_on']),
        format: asStr(j['format']),
        team: asStr(j['team']),
        opponent: asStr(j['opponent']),
        tournament: asStrOrNull(j['tournament']),
        venue: asStrOrNull(j['venue']),
        matchNo: asStrOrNull(j['match_no']),
        result: asStrOrNull(j['result']),
        outcome: asStr(j['outcome'], 'in_progress'),
        batted: asBool(j['batted']),
        runs: asIntOrNull(j['runs']),
        balls: asIntOrNull(j['balls']),
        fours: asInt(j['fours']),
        sixes: asInt(j['sixes']),
        strikeRate: asDoubleOrNull(j['strike_rate']),
        notOut: asBool(j['not_out']),
        howOut: asStrOrNull(j['how_out']),
        dismissalText: asStrOrNull(j['dismissal_text']),
        batLine: asStrOrNull(j['bat_line']),
        bowled: asBool(j['bowled']),
        overs: asStrOrNull(j['overs']),
        maidens: asInt(j['maidens']),
        runsConceded: asIntOrNull(j['runs_conceded']),
        wickets: asIntOrNull(j['wickets']),
        economy: asDoubleOrNull(j['economy']),
        bowlLine: asStrOrNull(j['bowl_line']),
        catches: asInt(j['catches']),
        runOuts: asInt(j['run_outs']),
        stumpings: asInt(j['stumpings']),
      );

  bool get isLive => outcome == 'in_progress';

  bool get tookAFieldingCredit => catches + runOuts + stumpings > 0;

  /// "2 catches · 1 run out" — only the parts that actually happened.
  String get fieldingLine {
    String plural(int n, String one, String many) => '$n ${n == 1 ? one : many}';
    return [
      if (catches > 0) plural(catches, 'catch', 'catches'),
      if (runOuts > 0) plural(runOuts, 'run out', 'run outs'),
      if (stumpings > 0) plural(stumpings, 'stumping', 'stumpings'),
    ].join(' · ');
  }

  /// A fifty or a hundred, for flagging a standout innings.
  bool get isMilestoneInnings => (runs ?? 0) >= 50;

  /// A three-for or better.
  bool get isStandoutSpell => (wickets ?? 0) >= 3;

  static const _outcomeLabels = <String, String>{
    'won': 'Won',
    'lost': 'Lost',
    'tied': 'Tied',
    'no_result': 'No result',
    'in_progress': 'Live',
  };

  String get outcomeLabel => _outcomeLabels[outcome] ?? outcome;
}

/// A player's record inside one grouping — a tournament, a year, or a side.
class CareerBucket {
  final String key;
  final String label;
  final int matches;
  final int won;
  final int lost;
  final BattingStats batting;
  final BowlingStats bowling;
  final FieldingStats fielding;

  const CareerBucket({
    required this.key,
    required this.label,
    this.matches = 0,
    this.won = 0,
    this.lost = 0,
    this.batting = const BattingStats(),
    this.bowling = const BowlingStats(),
    this.fielding = const FieldingStats(),
  });

  factory CareerBucket.fromJson(Map<String, dynamic> j) => CareerBucket(
        key: asStr(j['key']),
        label: asStr(j['label']),
        matches: asInt(j['matches']),
        won: asInt(j['won']),
        lost: asInt(j['lost']),
        batting: BattingStats.fromJson(asMap(j['batting'])),
        bowling: BowlingStats.fromJson(asMap(j['bowling'])),
        fielding: FieldingStats.fromJson(asMap(j['fielding'])),
      );

  /// A campaign is worth showing in full only if they did something in it.
  bool get hasBatting => batting.innings > 0;
  bool get hasBowling => bowling.balls > 0;
}

/// A player's whole record: every match, grouped every useful way.
class PlayerHistory {
  final Player player;
  final String? debut;
  final String? lastPlayed;
  final int matchesPlayed;
  final int won;
  final int lost;
  final int tied;
  final int noResult;
  final double winPct;

  final BattingStats batting;
  final BowlingStats bowling;
  final FieldingStats fielding;

  /// The entire career, newest first.
  final List<CareerMatch> matches;
  final List<CareerBucket> byTournament;
  final List<CareerBucket> byYear;
  final List<CareerBucket> byTeam;

  const PlayerHistory({
    required this.player,
    this.debut,
    this.lastPlayed,
    this.matchesPlayed = 0,
    this.won = 0,
    this.lost = 0,
    this.tied = 0,
    this.noResult = 0,
    this.winPct = 0,
    this.batting = const BattingStats(),
    this.bowling = const BowlingStats(),
    this.fielding = const FieldingStats(),
    this.matches = const [],
    this.byTournament = const [],
    this.byYear = const [],
    this.byTeam = const [],
  });

  factory PlayerHistory.fromJson(Map<String, dynamic> j) => PlayerHistory(
        player: Player.fromJson(asMap(j['player'])),
        debut: asStrOrNull(j['debut']),
        lastPlayed: asStrOrNull(j['last_played']),
        matchesPlayed: asInt(j['matches_played']),
        won: asInt(j['won']),
        lost: asInt(j['lost']),
        tied: asInt(j['tied']),
        noResult: asInt(j['no_result']),
        winPct: asDouble(j['win_pct']),
        batting: BattingStats.fromJson(asMap(j['batting'])),
        bowling: BowlingStats.fromJson(asMap(j['bowling'])),
        fielding: FieldingStats.fromJson(asMap(j['fielding'])),
        matches: asMapList(j['matches']).map(CareerMatch.fromJson).toList(),
        byTournament:
            asMapList(j['by_tournament']).map(CareerBucket.fromJson).toList(),
        byYear: asMapList(j['by_year']).map(CareerBucket.fromJson).toList(),
        byTeam: asMapList(j['by_team']).map(CareerBucket.fromJson).toList(),
      );

  bool get hasPlayed => matchesPlayed > 0;

  /// The best innings on record, for the career headline.
  CareerMatch? get bestInnings {
    CareerMatch? best;
    for (final m in matches) {
      if (!m.batted) continue;
      if (best == null || (m.runs ?? 0) > (best.runs ?? 0)) best = m;
    }
    return best;
  }

  /// The best spell on record.
  CareerMatch? get bestSpell {
    CareerMatch? best;
    for (final m in matches) {
      if (!m.bowled) continue;
      if (best == null ||
          (m.wickets ?? 0) > (best.wickets ?? 0) ||
          ((m.wickets ?? 0) == (best.wickets ?? 0) &&
              (m.runsConceded ?? 0) < (best.runsConceded ?? 0))) {
        best = m;
      }
    }
    return best;
  }

  /// Every distinct competition they have appeared in.
  List<String> get tournaments => [for (final t in byTournament) t.label];
}
