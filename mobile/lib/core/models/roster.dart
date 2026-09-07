/// Players, teams and their career/record statistics.
library;

import 'json.dart';

class Player {
  final String id;
  final String name;

  /// Stable roster code, e.g. "P00012" — tells same-named players apart.
  final String code;
  final String? phone;
  final String? battingStyle;
  final String? bowlingStyle;
  final bool hasPhoto;

  /// User id that claimed this roster profile; null when unclaimed.
  final String? claimedBy;

  const Player({
    required this.id,
    required this.name,
    this.code = '',
    this.phone,
    this.battingStyle,
    this.bowlingStyle,
    this.hasPhoto = false,
    this.claimedBy,
  });

  factory Player.fromJson(Map<String, dynamic> j) => Player(
        id: asStr(j['id']),
        name: asStr(j['name']),
        code: asStr(j['code']),
        phone: asStrOrNull(j['phone']),
        battingStyle: asStrOrNull(j['batting_style']),
        bowlingStyle: asStrOrNull(j['bowling_style']),
        hasPhoto: asBool(j['has_photo']),
        claimedBy: asStrOrNull(j['claimed_by']),
      );

  /// "Right-hand bat · Right-arm fast", or a neutral fallback.
  String get styleLine {
    final parts = <String>[
      if (battingStyle != null && battingStyle!.isNotEmpty) battingStyle!,
      if (bowlingStyle != null && bowlingStyle!.isNotEmpty) bowlingStyle!,
    ];
    return parts.isEmpty ? 'Cricketer' : parts.join(' · ');
  }

  bool get isClaimed => claimedBy != null && claimedBy!.isNotEmpty;

  /// The styles offered by the web app's player form.
  static const battingStyles = <String>['Right-hand bat', 'Left-hand bat'];

  static const bowlingStyles = <String>[
    'Right-arm fast',
    'Right-arm medium',
    'Right-arm off-spin',
    'Right-arm leg-spin',
    'Left-arm fast',
    'Left-arm medium',
    'Left-arm orthodox',
    'Left-arm wrist-spin',
  ];
}

class TeamMember {
  final String playerId;
  final String name;
  final String code;
  final bool isCaptain;
  final bool hasPhoto;

  const TeamMember({
    required this.playerId,
    required this.name,
    this.code = '',
    this.isCaptain = false,
    this.hasPhoto = false,
  });

  factory TeamMember.fromJson(Map<String, dynamic> j) => TeamMember(
        playerId: asStr(j['player_id']),
        name: asStr(j['name']),
        code: asStr(j['code']),
        isCaptain: asBool(j['is_captain']),
        hasPhoto: asBool(j['has_photo']),
      );
}

class Team {
  final String id;
  final String name;
  final String? location;
  final List<TeamMember> members;
  final bool hasPhoto;

  const Team({
    required this.id,
    required this.name,
    this.location,
    this.members = const [],
    this.hasPhoto = false,
  });

  factory Team.fromJson(Map<String, dynamic> j) => Team(
        id: asStr(j['id']),
        name: asStr(j['name']),
        location: asStrOrNull(j['location']),
        members: asMapList(j['members']).map(TeamMember.fromJson).toList(),
        hasPhoto: asBool(j['has_photo']),
      );

  /// "11 players · Mumbai"
  String get subtitle {
    final n = members.length;
    final base = '$n player${n == 1 ? '' : 's'}';
    return location == null || location!.isEmpty ? base : '$base · $location';
  }
}

class TeamStats {
  final String teamId;
  final String name;
  final int played;
  final int won;
  final int lost;
  final int tied;
  final int noResult;
  final double winPct;
  final int runsFor;
  final int runsAgainst;

  const TeamStats({
    required this.teamId,
    this.name = '',
    this.played = 0,
    this.won = 0,
    this.lost = 0,
    this.tied = 0,
    this.noResult = 0,
    this.winPct = 0,
    this.runsFor = 0,
    this.runsAgainst = 0,
  });

  factory TeamStats.fromJson(Map<String, dynamic> j) => TeamStats(
        teamId: asStr(j['team_id']),
        name: asStr(j['name']),
        played: asInt(j['played']),
        won: asInt(j['won']),
        lost: asInt(j['lost']),
        tied: asInt(j['tied']),
        noResult: asInt(j['no_result']),
        winPct: asDouble(j['win_pct']),
        runsFor: asInt(j['runs_for']),
        runsAgainst: asInt(j['runs_against']),
      );

  int get netRuns => runsFor - runsAgainst;
}

class BattingStats {
  final int matches;
  final int innings;
  final int notOuts;
  final int runs;
  final int balls;
  final int highest;

  /// Null when the batter has never been dismissed.
  final double? average;
  final double strikeRate;
  final int fours;
  final int sixes;
  final int fifties;
  final int hundreds;

  const BattingStats({
    this.matches = 0,
    this.innings = 0,
    this.notOuts = 0,
    this.runs = 0,
    this.balls = 0,
    this.highest = 0,
    this.average,
    this.strikeRate = 0,
    this.fours = 0,
    this.sixes = 0,
    this.fifties = 0,
    this.hundreds = 0,
  });

  factory BattingStats.fromJson(Map<String, dynamic> j) => BattingStats(
        matches: asInt(j['matches']),
        innings: asInt(j['innings']),
        notOuts: asInt(j['not_outs']),
        runs: asInt(j['runs']),
        balls: asInt(j['balls']),
        highest: asInt(j['highest']),
        average: asDoubleOrNull(j['average']),
        strikeRate: asDouble(j['strike_rate']),
        fours: asInt(j['fours']),
        sixes: asInt(j['sixes']),
        fifties: asInt(j['fifties']),
        hundreds: asInt(j['hundreds']),
      );

  bool get hasPlayed => innings > 0 || runs > 0;
}

class BowlingStats {
  final int matches;
  final int innings;
  final int balls;
  final String overs;
  final int maidens;
  final int runs;
  final int wickets;

  /// Null when no wickets have been taken.
  final double? average;
  final double economy;
  final double? strikeRate;
  final String best;

  const BowlingStats({
    this.matches = 0,
    this.innings = 0,
    this.balls = 0,
    this.overs = '0.0',
    this.maidens = 0,
    this.runs = 0,
    this.wickets = 0,
    this.average,
    this.economy = 0,
    this.strikeRate,
    this.best = '-',
  });

  factory BowlingStats.fromJson(Map<String, dynamic> j) => BowlingStats(
        matches: asInt(j['matches']),
        innings: asInt(j['innings']),
        balls: asInt(j['balls']),
        overs: asStr(j['overs'], '0.0'),
        maidens: asInt(j['maidens']),
        runs: asInt(j['runs']),
        wickets: asInt(j['wickets']),
        average: asDoubleOrNull(j['average']),
        economy: asDouble(j['economy']),
        strikeRate: asDoubleOrNull(j['strike_rate']),
        best: asStr(j['best'], '-'),
      );

  bool get hasBowled => balls > 0;
}

class FieldingStats {
  final int catches;
  final int runOuts;
  final int stumpings;
  final int drops;
  final int runsSaved;

  const FieldingStats({
    this.catches = 0,
    this.runOuts = 0,
    this.stumpings = 0,
    this.drops = 0,
    this.runsSaved = 0,
  });

  factory FieldingStats.fromJson(Map<String, dynamic> j) => FieldingStats(
        catches: asInt(j['catches']),
        runOuts: asInt(j['run_outs']),
        stumpings: asInt(j['stumpings']),
        drops: asInt(j['drops']),
        runsSaved: asInt(j['runs_saved']),
      );
}

/// One line of a player's recent form.
class FormEntry {
  final String matchId;
  final String teams;
  final String? bat;
  final String? bowl;

  const FormEntry({
    required this.matchId,
    this.teams = '',
    this.bat,
    this.bowl,
  });

  factory FormEntry.fromJson(Map<String, dynamic> j) => FormEntry(
        matchId: asStr(j['match_id']),
        teams: asStr(j['teams']),
        bat: asStrOrNull(j['bat']),
        bowl: asStrOrNull(j['bowl']),
      );
}

class PlayerStats {
  final Player player;
  final BattingStats batting;
  final BowlingStats bowling;
  final FieldingStats fielding;
  final List<FormEntry> recent;

  const PlayerStats({
    required this.player,
    this.batting = const BattingStats(),
    this.bowling = const BowlingStats(),
    this.fielding = const FieldingStats(),
    this.recent = const [],
  });

  factory PlayerStats.fromJson(Map<String, dynamic> j) => PlayerStats(
        player: Player.fromJson(asMap(j['player'])),
        batting: BattingStats.fromJson(asMap(j['batting'])),
        bowling: BowlingStats.fromJson(asMap(j['bowling'])),
        fielding: FieldingStats.fromJson(asMap(j['fielding'])),
        recent: asMapList(j['recent']).map(FormEntry.fromJson).toList(),
      );
}

class BattingInsights {
  final int ballsFaced;
  final int dotBalls;
  final double dotPct;
  final int fours;
  final int sixes;
  final double boundaryPct;
  final int boundaryRuns;
  final int runningRuns;
  final double boundaryRunsPct;
  final Map<String, int> dismissals;
  final double sixPct;
  final int shotsTracked;
  final double offSidePct;
  final double legSidePct;
  final String topZone;
  final Map<String, int> runsByZone;

  const BattingInsights({
    this.ballsFaced = 0,
    this.dotBalls = 0,
    this.dotPct = 0,
    this.fours = 0,
    this.sixes = 0,
    this.boundaryPct = 0,
    this.boundaryRuns = 0,
    this.runningRuns = 0,
    this.boundaryRunsPct = 0,
    this.dismissals = const {},
    this.sixPct = 0,
    this.shotsTracked = 0,
    this.offSidePct = 0,
    this.legSidePct = 0,
    this.topZone = '',
    this.runsByZone = const {},
  });

  factory BattingInsights.fromJson(Map<String, dynamic> j) => BattingInsights(
        ballsFaced: asInt(j['balls_faced']),
        dotBalls: asInt(j['dot_balls']),
        dotPct: asDouble(j['dot_pct']),
        fours: asInt(j['fours']),
        sixes: asInt(j['sixes']),
        boundaryPct: asDouble(j['boundary_pct']),
        boundaryRuns: asInt(j['boundary_runs']),
        runningRuns: asInt(j['running_runs']),
        boundaryRunsPct: asDouble(j['boundary_runs_pct']),
        dismissals: asIntMap(j['dismissals']),
        sixPct: asDouble(j['six_pct']),
        shotsTracked: asInt(j['shots_tracked']),
        offSidePct: asDouble(j['off_side_pct']),
        legSidePct: asDouble(j['leg_side_pct']),
        topZone: asStr(j['top_zone']),
        runsByZone: asIntMap(j['runs_by_zone']),
      );
}

class BowlingInsights {
  final int ballsBowled;
  final int dotBalls;
  final double dotPct;
  final Map<String, int> wicketsByType;
  final int pitchesTracked;
  final Map<String, int> lengthDist;
  final Map<String, double> econByLength;

  const BowlingInsights({
    this.ballsBowled = 0,
    this.dotBalls = 0,
    this.dotPct = 0,
    this.wicketsByType = const {},
    this.pitchesTracked = 0,
    this.lengthDist = const {},
    this.econByLength = const {},
  });

  factory BowlingInsights.fromJson(Map<String, dynamic> j) => BowlingInsights(
        ballsBowled: asInt(j['balls_bowled']),
        dotBalls: asInt(j['dot_balls']),
        dotPct: asDouble(j['dot_pct']),
        wicketsByType: asIntMap(j['wickets_by_type']),
        pitchesTracked: asInt(j['pitches_tracked']),
        lengthDist: asIntMap(j['length_dist']),
        econByLength: asDoubleMap(j['econ_by_length']),
      );
}

class PlayerInsights {
  final Player player;
  final BattingInsights batting;
  final BowlingInsights bowling;

  const PlayerInsights({
    required this.player,
    this.batting = const BattingInsights(),
    this.bowling = const BowlingInsights(),
  });

  factory PlayerInsights.fromJson(Map<String, dynamic> j) => PlayerInsights(
        player: Player.fromJson(asMap(j['player'])),
        batting: BattingInsights.fromJson(asMap(j['batting'])),
        bowling: BowlingInsights.fromJson(asMap(j['bowling'])),
      );
}

/// A career slice — by format, or by ball type.
class FormatSplit {
  final String key;
  final String label;
  final int matches;
  final BattingStats batting;
  final BowlingStats bowling;

  const FormatSplit({
    required this.key,
    this.label = '',
    this.matches = 0,
    this.batting = const BattingStats(),
    this.bowling = const BowlingStats(),
  });

  factory FormatSplit.fromJson(Map<String, dynamic> j) => FormatSplit(
        key: asStr(j['key']),
        label: asStr(j['label']),
        matches: asInt(j['matches']),
        batting: BattingStats.fromJson(asMap(j['batting'])),
        bowling: BowlingStats.fromJson(asMap(j['bowling'])),
      );
}

/// Batting record against pace or spin.
class BattingVsType {
  final String label;
  final int balls;
  final int runs;
  final int dotBalls;
  final double dotPct;
  final int fours;
  final int sixes;
  final double strikeRate;
  final int dismissals;
  final double? average;

  const BattingVsType({
    this.label = '',
    this.balls = 0,
    this.runs = 0,
    this.dotBalls = 0,
    this.dotPct = 0,
    this.fours = 0,
    this.sixes = 0,
    this.strikeRate = 0,
    this.dismissals = 0,
    this.average,
  });

  factory BattingVsType.fromJson(Map<String, dynamic> j) => BattingVsType(
        label: asStr(j['label']),
        balls: asInt(j['balls']),
        runs: asInt(j['runs']),
        dotBalls: asInt(j['dot_balls']),
        dotPct: asDouble(j['dot_pct']),
        fours: asInt(j['fours']),
        sixes: asInt(j['sixes']),
        strikeRate: asDouble(j['strike_rate']),
        dismissals: asInt(j['dismissals']),
        average: asDoubleOrNull(j['average']),
      );
}

class PlayerSplits {
  final Player player;
  final List<FormatSplit> byFormat;
  final List<FormatSplit> byBall;
  final BattingVsType vsPace;
  final BattingVsType vsSpin;
  final bool hasMatchup;

  const PlayerSplits({
    required this.player,
    this.byFormat = const [],
    this.byBall = const [],
    this.vsPace = const BattingVsType(),
    this.vsSpin = const BattingVsType(),
    this.hasMatchup = false,
  });

  factory PlayerSplits.fromJson(Map<String, dynamic> j) => PlayerSplits(
        player: Player.fromJson(asMap(j['player'])),
        byFormat: asMapList(j['by_format']).map(FormatSplit.fromJson).toList(),
        byBall: asMapList(j['by_ball']).map(FormatSplit.fromJson).toList(),
        vsPace: BattingVsType.fromJson(asMap(j['vs_pace'])),
        vsSpin: BattingVsType.fromJson(asMap(j['vs_spin'])),
        hasMatchup: asBool(j['has_matchup']),
      );
}

/// A match award won by a player.
class PlayerAward {
  final String matchId;

  /// mom | best_bat | best_bowl
  final String awardType;
  final String playerName;
  final String detail;
  final String when;

  const PlayerAward({
    required this.matchId,
    this.awardType = '',
    this.playerName = '',
    this.detail = '',
    this.when = '',
  });

  factory PlayerAward.fromJson(Map<String, dynamic> j) => PlayerAward(
        matchId: asStr(j['match_id']),
        awardType: asStr(j['award_type']),
        playerName: asStr(j['player_name']),
        detail: asStr(j['detail']),
        when: asStr(j['when']),
      );

  String get label => switch (awardType) {
        'mom' => 'Player of the Match',
        'best_bat' => 'Best batter',
        'best_bowl' => 'Best bowler',
        _ => 'Award',
      };

  String get emoji => switch (awardType) {
        'mom' => '⭐',
        'best_bat' => '\u{1f3cf}',
        'best_bowl' => '\u{1f3af}',
        _ => '\u{1f3c5}',
      };
}

/// Head-to-head comparison from `GET /insights/compare`.
class PlayerCompare {
  final PlayerStats playerA;
  final PlayerStats playerB;

  const PlayerCompare({required this.playerA, required this.playerB});

  factory PlayerCompare.fromJson(Map<String, dynamic> j) => PlayerCompare(
        playerA: PlayerStats.fromJson(asMap(j['player_a'])),
        playerB: PlayerStats.fromJson(asMap(j['player_b'])),
      );
}
