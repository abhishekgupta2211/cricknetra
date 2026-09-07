/// Tournaments — leagues, knockouts and group-stage competitions.
library;

import 'json.dart';
import 'roster.dart';

class TeamRef {
  final String id;
  final String name;

  const TeamRef({required this.id, required this.name});

  factory TeamRef.fromJson(Map<String, dynamic> j) =>
      TeamRef(id: asStr(j['id']), name: asStr(j['name']));
}

/// Competition shapes the backend accepts.
class TournamentFormats {
  const TournamentFormats._();
  static const roundRobin = 'round_robin';
  static const knockout = 'knockout';
  static const groups = 'groups';

  static const all = <String>[roundRobin, groups, knockout];

  static String label(String v) => switch (v) {
        roundRobin => 'League',
        knockout => 'Knockout',
        groups => 'Groups + playoffs',
        _ => v,
      };

  static String blurb(String v) => switch (v) {
        roundRobin => 'Everyone plays everyone. Points table with net run rate.',
        knockout => 'Single elimination. Lose once and you are out.',
        groups => 'Pools first, then a seeded knockout playoff.',
        _ => '',
      };
}

class Fixture {
  final String id;
  final int round;
  final int position;
  final TeamRef? teamA;
  final TeamRef? teamB;
  final String? matchId;

  /// scheduled | live | completed
  final String status;
  final String? result;

  /// Pool label ("A", "B", …); null for a playoff or bracket fixture.
  final String? group;

  const Fixture({
    required this.id,
    this.round = 1,
    this.position = 1,
    this.teamA,
    this.teamB,
    this.matchId,
    this.status = 'scheduled',
    this.result,
    this.group,
  });

  factory Fixture.fromJson(Map<String, dynamic> j) => Fixture(
        id: asStr(j['id']),
        round: asInt(j['round'], 1),
        position: asInt(j['position'], 1),
        teamA: j['team_a'] is Map ? TeamRef.fromJson(asMap(j['team_a'])) : null,
        teamB: j['team_b'] is Map ? TeamRef.fromJson(asMap(j['team_b'])) : null,
        matchId: asStrOrNull(j['match_id']),
        status: asStr(j['status'], 'scheduled'),
        result: asStrOrNull(j['result']),
        group: asStrOrNull(j['group']),
      );

  bool get isCompleted => status == 'completed';
  bool get isLive => status == 'live';
  bool get isScheduled => status == 'scheduled';

  /// A team drawing a bye has no opponent.
  bool get isBye => result == 'bye' || teamB == null;

  String get title {
    final a = teamA?.name ?? 'TBD';
    final b = teamB?.name ?? (isBye ? 'Bye' : 'TBD');
    return '$a v $b';
  }
}

class StandingRow {
  final String teamId;
  final String name;
  final int played;
  final int won;
  final int lost;
  final int tied;
  final int noResult;
  final int points;
  final double nrr;

  const StandingRow({
    required this.teamId,
    this.name = '',
    this.played = 0,
    this.won = 0,
    this.lost = 0,
    this.tied = 0,
    this.noResult = 0,
    this.points = 0,
    this.nrr = 0,
  });

  factory StandingRow.fromJson(Map<String, dynamic> j) => StandingRow(
        teamId: asStr(j['team_id']),
        name: asStr(j['name']),
        played: asInt(j['played']),
        won: asInt(j['won']),
        lost: asInt(j['lost']),
        tied: asInt(j['tied']),
        noResult: asInt(j['no_result']),
        points: asInt(j['points']),
        nrr: asDouble(j['nrr']),
      );

  /// Net run rate with an explicit sign, the way points tables print it.
  String get nrrText =>
      '${nrr >= 0 ? '+' : ''}${nrr.toStringAsFixed(3)}';
}

class GroupStanding {
  final String group;
  final List<StandingRow> standings;

  const GroupStanding({required this.group, this.standings = const []});

  factory GroupStanding.fromJson(Map<String, dynamic> j) => GroupStanding(
        group: asStr(j['group']),
        standings: asMapList(j['standings']).map(StandingRow.fromJson).toList(),
      );
}

class TournamentSummary {
  final String id;
  final String name;
  final String format;
  final String status;
  final List<TeamRef> teams;

  const TournamentSummary({
    required this.id,
    this.name = '',
    this.format = TournamentFormats.roundRobin,
    this.status = 'active',
    this.teams = const [],
  });

  factory TournamentSummary.fromJson(Map<String, dynamic> j) =>
      TournamentSummary(
        id: asStr(j['id']),
        name: asStr(j['name']),
        format: asStr(j['format'], TournamentFormats.roundRobin),
        status: asStr(j['status'], 'active'),
        teams: asMapList(j['teams']).map(TeamRef.fromJson).toList(),
      );

  String get subtitle =>
      '${teams.length} teams · ${TournamentFormats.label(format)}';
}

class Tournament {
  final String id;
  final String name;
  final String format;
  final String status;
  final List<TeamRef> teams;
  final List<Fixture> fixtures;

  /// Flat league table (round_robin); empty for groups and knockout.
  final List<StandingRow> standings;

  /// Per-pool tables (groups format).
  final List<GroupStanding> groups;
  final TeamRef? champion;

  /// Echo of the points and group settings.
  final Map<String, dynamic> config;

  const Tournament({
    required this.id,
    this.name = '',
    this.format = TournamentFormats.roundRobin,
    this.status = 'active',
    this.teams = const [],
    this.fixtures = const [],
    this.standings = const [],
    this.groups = const [],
    this.champion,
    this.config = const {},
  });

  factory Tournament.fromJson(Map<String, dynamic> j) => Tournament(
        id: asStr(j['id']),
        name: asStr(j['name']),
        format: asStr(j['format'], TournamentFormats.roundRobin),
        status: asStr(j['status'], 'active'),
        teams: asMapList(j['teams']).map(TeamRef.fromJson).toList(),
        fixtures: asMapList(j['fixtures']).map(Fixture.fromJson).toList(),
        standings: asMapList(j['standings']).map(StandingRow.fromJson).toList(),
        groups: asMapList(j['groups']).map(GroupStanding.fromJson).toList(),
        champion: j['champion'] is Map
            ? TeamRef.fromJson(asMap(j['champion']))
            : null,
        config: asMap(j['config']),
      );

  bool get isKnockout => format == TournamentFormats.knockout;
  bool get isGroups => format == TournamentFormats.groups;
  bool get isLeague => format == TournamentFormats.roundRobin;

  bool get dlsEnabled => asBool(config['dls_enabled']);

  /// Bracket fixtures — knockout rounds, or the playoffs of a groups event.
  List<Fixture> get bracketFixtures =>
      fixtures.where((f) => f.group == null).toList();

  List<Fixture> fixturesInGroup(String group) =>
      fixtures.where((f) => f.group == group).toList();

  /// Fixtures bucketed by round, in round order.
  Map<int, List<Fixture>> roundsOf(List<Fixture> source) {
    final out = <int, List<Fixture>>{};
    for (final f in source) {
      out.putIfAbsent(f.round, () => []).add(f);
    }
    return Map.fromEntries(
      out.entries.toList()..sort((a, b) => a.key.compareTo(b.key)),
    );
  }

  /// Knockout rounds get named from the end: Final, Semi-finals, and so on.
  static String roundLabel(int round, int totalRounds, {bool knockout = true}) {
    if (!knockout) return 'Round $round';
    final fromEnd = totalRounds - round;
    return switch (fromEnd) {
      0 => 'Final',
      1 => 'Semi-finals',
      2 => 'Quarter-finals',
      _ => 'Round $round',
    };
  }
}

/// A team's registered squad for one tournament.
class TeamSquad {
  final String teamId;
  final String teamName;
  final List<Player> players;

  const TeamSquad({
    required this.teamId,
    this.teamName = '',
    this.players = const [],
  });

  factory TeamSquad.fromJson(Map<String, dynamic> j) => TeamSquad(
        teamId: asStr(j['team_id']),
        teamName: asStr(j['team_name']),
        players: asMapList(j['players']).map(Player.fromJson).toList(),
      );
}
