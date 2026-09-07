/// Match state and its projections — the shape every scoring call returns.
///
/// The server folds the append-only ball log into this on every request, so the
/// client never derives a score itself: it renders whatever came back.
library;

import 'json.dart';
import 'rules.dart';

class Extras {
  final int wides;
  final int noBalls;
  final int byes;
  final int legByes;
  final int penalty;
  final int total;

  const Extras({
    this.wides = 0,
    this.noBalls = 0,
    this.byes = 0,
    this.legByes = 0,
    this.penalty = 0,
    this.total = 0,
  });

  factory Extras.fromJson(Map<String, dynamic> j) => Extras(
        wides: asInt(j['wides']),
        noBalls: asInt(j['no_balls']),
        byes: asInt(j['byes']),
        legByes: asInt(j['leg_byes']),
        penalty: asInt(j['penalty']),
        total: asInt(j['total']),
      );

  /// "3w 1nb 2lb" — the parts that are actually non-zero.
  String get breakdown {
    final parts = <String>[
      if (wides > 0) '${wides}w',
      if (noBalls > 0) '${noBalls}nb',
      if (byes > 0) '${byes}b',
      if (legByes > 0) '${legByes}lb',
      if (penalty > 0) '${penalty}p',
    ];
    return parts.isEmpty ? '—' : parts.join(' ');
  }
}

class BatterCard {
  final String name;
  final int order;
  final int runs;
  final int balls;
  final int fours;
  final int sixes;
  final bool out;
  final String? howOut;
  final String? dismissalText;
  final bool onStrike;
  final bool hasBatted;
  final double strikeRate;

  /// Roster id when the match was created from real teams; null for ad-hoc names.
  final String? playerId;

  const BatterCard({
    required this.name,
    this.order = 0,
    this.runs = 0,
    this.balls = 0,
    this.fours = 0,
    this.sixes = 0,
    this.out = false,
    this.howOut,
    this.dismissalText,
    this.onStrike = false,
    this.hasBatted = false,
    this.strikeRate = 0,
    this.playerId,
  });

  factory BatterCard.fromJson(Map<String, dynamic> j) => BatterCard(
        name: asStr(j['name']),
        order: asInt(j['order']),
        runs: asInt(j['runs']),
        balls: asInt(j['balls']),
        fours: asInt(j['fours']),
        sixes: asInt(j['sixes']),
        out: asBool(j['out']),
        howOut: asStrOrNull(j['how_out']),
        dismissalText: asStrOrNull(j['dismissal_text']),
        onStrike: asBool(j['on_strike']),
        hasBatted: asBool(j['has_batted']),
        strikeRate: asDouble(j['strike_rate']),
        playerId: asStrOrNull(j['player_id']),
      );

  /// "45 (30)"
  String get figure => '$runs ($balls)';

  String get statusText => out ? (dismissalText ?? 'out') : 'not out';
}

class BowlerCard {
  final String name;
  final int order;
  final String overs;
  final int maidens;
  final int runs;
  final int wickets;
  final double economy;
  final int wides;
  final int noBalls;
  final String? playerId;

  const BowlerCard({
    required this.name,
    this.order = 0,
    this.overs = '0.0',
    this.maidens = 0,
    this.runs = 0,
    this.wickets = 0,
    this.economy = 0,
    this.wides = 0,
    this.noBalls = 0,
    this.playerId,
  });

  factory BowlerCard.fromJson(Map<String, dynamic> j) => BowlerCard(
        name: asStr(j['name']),
        order: asInt(j['order']),
        overs: asStr(j['overs'], '0.0'),
        maidens: asInt(j['maidens']),
        runs: asInt(j['runs']),
        wickets: asInt(j['wickets']),
        economy: asDouble(j['economy']),
        wides: asInt(j['wides']),
        noBalls: asInt(j['no_balls']),
        playerId: asStrOrNull(j['player_id']),
      );

  /// "2/24 (4.0)"
  String get figure => '$wickets/$runs ($overs)';
}

class FallOfWicket {
  final int wicket;
  final int score;
  final String batterOut;
  final String over;

  const FallOfWicket({
    required this.wicket,
    required this.score,
    required this.batterOut,
    required this.over,
  });

  factory FallOfWicket.fromJson(Map<String, dynamic> j) => FallOfWicket(
        wicket: asInt(j['wicket']),
        score: asInt(j['score']),
        batterOut: asStr(j['batter_out']),
        over: asStr(j['over'], '0.0'),
      );

  /// "13-1 (Rohit Sharma, 1.0)"
  String get label => '$score-$wicket ($batterOut, $over)';
}

class Partnership {
  final int wicket;
  final int runs;
  final int balls;
  final String batterA;
  final String batterB;
  final bool unbroken;
  final double runRate;

  const Partnership({
    required this.wicket,
    this.runs = 0,
    this.balls = 0,
    this.batterA = '',
    this.batterB = '',
    this.unbroken = false,
    this.runRate = 0,
  });

  factory Partnership.fromJson(Map<String, dynamic> j) => Partnership(
        wicket: asInt(j['wicket']),
        runs: asInt(j['runs']),
        balls: asInt(j['balls']),
        batterA: asStr(j['batter_a']),
        batterB: asStr(j['batter_b']),
        unbroken: asBool(j['unbroken']),
        runRate: asDouble(j['run_rate']),
      );
}

/// One scoring shot for the wagon wheel. `x` runs leg (-1) to off (+1),
/// `y` runs behind square (-1) to straight (+1).
class WagonPoint {
  final double x;
  final double y;
  final int runs;
  final String batter;
  final String over;
  final String ball;
  final String bowler;
  final bool wicket;
  final String zone;

  const WagonPoint({
    required this.x,
    required this.y,
    this.runs = 0,
    this.batter = '',
    this.over = '',
    this.ball = '',
    this.bowler = '',
    this.wicket = false,
    this.zone = '',
  });

  factory WagonPoint.fromJson(Map<String, dynamic> j) => WagonPoint(
        x: asDouble(j['x']),
        y: asDouble(j['y']),
        runs: asInt(j['runs']),
        batter: asStr(j['batter']),
        over: asStr(j['over']),
        ball: asStr(j['ball']),
        bowler: asStr(j['bowler']),
        wicket: asBool(j['wicket']),
        zone: asStr(j['zone']),
      );
}

/// One delivery on the pitch map. `x` is line (-1 down-leg .. +1 wide-off),
/// `y` is length (0 yorker .. 1 bouncer).
class PitchMark {
  final double x;
  final double y;
  final int runs;
  final bool wicket;
  final String bowler;
  final String batter;
  final String over;
  final double? speed;
  final String length;
  final String line;
  final String outcome;

  const PitchMark({
    required this.x,
    required this.y,
    this.runs = 0,
    this.wicket = false,
    this.bowler = '',
    this.batter = '',
    this.over = '',
    this.speed,
    this.length = '',
    this.line = '',
    this.outcome = '',
  });

  factory PitchMark.fromJson(Map<String, dynamic> j) => PitchMark(
        x: asDouble(j['x']),
        y: asDouble(j['y']),
        runs: asInt(j['runs']),
        wicket: asBool(j['wicket']),
        bowler: asStr(j['bowler']),
        batter: asStr(j['batter']),
        over: asStr(j['over']),
        speed: asDoubleOrNull(j['speed']),
        length: asStr(j['length']),
        line: asStr(j['line']),
        outcome: asStr(j['outcome']),
      );
}

class Innings {
  final String battingTeam;
  final String bowlingTeam;
  final int runs;
  final int wickets;
  final int legalBalls;
  final String oversStr;
  final int maxOvers;
  final int maxWickets;
  final Extras extras;
  final double runRate;
  final List<BatterCard> batters;
  final List<BowlerCard> bowlers;
  final List<FallOfWicket> fallOfWickets;
  final List<Partnership> partnerships;
  final List<String> thisOver;
  final List<int> manhattan;
  final List<int> worm;
  final List<WagonPoint> wagon;
  final List<PitchMark> pitch;
  final String? striker;
  final String? nonStriker;
  final String? bowler;
  final bool freeHit;
  final bool isComplete;
  final int? target;
  final int? requiredRuns;
  final int? ballsRemaining;
  final double? requiredRunRate;
  final String? resultNote;
  final int currentOver;
  final bool inPowerplay;
  final String? powerplayLabel;
  final int? fieldersOutsideLimit;
  final bool isSuperOver;

  const Innings({
    this.battingTeam = '',
    this.bowlingTeam = '',
    this.runs = 0,
    this.wickets = 0,
    this.legalBalls = 0,
    this.oversStr = '0.0',
    this.maxOvers = 0,
    this.maxWickets = 0,
    this.extras = const Extras(),
    this.runRate = 0,
    this.batters = const [],
    this.bowlers = const [],
    this.fallOfWickets = const [],
    this.partnerships = const [],
    this.thisOver = const [],
    this.manhattan = const [],
    this.worm = const [],
    this.wagon = const [],
    this.pitch = const [],
    this.striker,
    this.nonStriker,
    this.bowler,
    this.freeHit = false,
    this.isComplete = false,
    this.target,
    this.requiredRuns,
    this.ballsRemaining,
    this.requiredRunRate,
    this.resultNote,
    this.currentOver = 1,
    this.inPowerplay = false,
    this.powerplayLabel,
    this.fieldersOutsideLimit,
    this.isSuperOver = false,
  });

  factory Innings.fromJson(Map<String, dynamic> j) => Innings(
        battingTeam: asStr(j['batting_team']),
        bowlingTeam: asStr(j['bowling_team']),
        runs: asInt(j['runs']),
        wickets: asInt(j['wickets']),
        legalBalls: asInt(j['legal_balls']),
        oversStr: asStr(j['overs_str'], '0.0'),
        maxOvers: asInt(j['max_overs']),
        maxWickets: asInt(j['max_wickets']),
        extras: Extras.fromJson(asMap(j['extras'])),
        runRate: asDouble(j['run_rate']),
        batters: asMapList(j['batters']).map(BatterCard.fromJson).toList(),
        bowlers: asMapList(j['bowlers']).map(BowlerCard.fromJson).toList(),
        fallOfWickets:
            asMapList(j['fall_of_wickets']).map(FallOfWicket.fromJson).toList(),
        partnerships:
            asMapList(j['partnerships']).map(Partnership.fromJson).toList(),
        thisOver: asStrList(j['this_over']),
        manhattan: (j['manhattan'] as List? ?? const [])
            .map((e) => asInt(e))
            .toList(),
        worm: (j['worm'] as List? ?? const []).map((e) => asInt(e)).toList(),
        wagon: asMapList(j['wagon']).map(WagonPoint.fromJson).toList(),
        pitch: asMapList(j['pitch']).map(PitchMark.fromJson).toList(),
        striker: asStrOrNull(j['striker']),
        nonStriker: asStrOrNull(j['non_striker']),
        bowler: asStrOrNull(j['bowler']),
        freeHit: asBool(j['free_hit']),
        isComplete: asBool(j['is_complete']),
        target: asIntOrNull(j['target']),
        requiredRuns: asIntOrNull(j['required_runs']),
        ballsRemaining: asIntOrNull(j['balls_remaining']),
        requiredRunRate: asDoubleOrNull(j['required_run_rate']),
        resultNote: asStrOrNull(j['result_note']),
        currentOver: asInt(j['current_over'], 1),
        inPowerplay: asBool(j['in_powerplay']),
        powerplayLabel: asStrOrNull(j['powerplay_label']),
        fieldersOutsideLimit: asIntOrNull(j['fielders_outside_limit']),
        isSuperOver: asBool(j['is_super_over']),
      );

  /// "128/4"
  String get scoreLine => '$runs/$wickets';

  bool get isChase => target != null;

  int get wicketsLeft => maxWickets - wickets;

  /// Runs the side is on course for at the current rate.
  int get projected => (runRate * maxOvers).round();

  List<BatterCard> get whoBatted => batters.where((b) => b.hasBatted).toList();

  BatterCard? get strikerCard => _find(striker);
  BatterCard? get nonStrikerCard => _find(nonStriker);

  BatterCard? _find(String? name) {
    if (name == null) return null;
    for (final b in batters) {
      if (b.name == name) return b;
    }
    return null;
  }

  BowlerCard? get currentBowler {
    if (bowler == null) return null;
    for (final b in bowlers) {
      if (b.name == bowler) return b;
    }
    return null;
  }

  Partnership? get currentPartnership {
    for (final p in partnerships) {
      if (p.unbroken) return p;
    }
    return null;
  }
}

class AwardEntry {
  final String name;
  final String? team;
  final String line;

  const AwardEntry({required this.name, this.team, this.line = ''});

  factory AwardEntry.fromJson(Map<String, dynamic> j) => AwardEntry(
        name: asStr(j['name']),
        team: asStrOrNull(j['team']),
        line: asStr(j['line']),
      );
}

class MatchAwards {
  final AwardEntry? manOfTheMatch;
  final AwardEntry? bestBatter;
  final AwardEntry? bestBowler;

  const MatchAwards({this.manOfTheMatch, this.bestBatter, this.bestBowler});

  factory MatchAwards.fromJson(Map<String, dynamic> j) {
    AwardEntry? pick(String key) {
      final m = asMapOrNull(j[key]);
      return m == null ? null : AwardEntry.fromJson(m);
    }

    return MatchAwards(
      manOfTheMatch: pick('man_of_the_match'),
      bestBatter: pick('best_batter'),
      bestBowler: pick('best_bowler'),
    );
  }

  bool get isEmpty =>
      manOfTheMatch == null && bestBatter == null && bestBowler == null;
}

/// A highlight clip — either a bring-your-own link or a server-cut mp4.
class MatchClip {
  final String id;
  final String url;
  final String? label;

  /// youtube | facebook | external | video
  final String kind;
  final String? embedUrl;

  /// "link" (embeddable) or "auto" (server-cut mp4 that plays inline).
  final String source;

  const MatchClip({
    required this.id,
    required this.url,
    this.label,
    this.kind = 'external',
    this.embedUrl,
    this.source = 'link',
  });

  factory MatchClip.fromJson(Map<String, dynamic> j) => MatchClip(
        id: asStr(j['id']),
        url: asStr(j['url']),
        label: asStrOrNull(j['label']),
        kind: asStr(j['kind'], 'external'),
        embedUrl: asStrOrNull(j['embed_url']),
        source: asStr(j['source'], 'link'),
      );

  bool get isVideoFile => kind == 'video' || source == 'auto';
  bool get isEmbeddable => embedUrl != null && embedUrl!.isNotEmpty;
}

/// Bring-your-own live stream attached to a match.
class StreamInfo {
  final String url;
  final String kind;
  final String? embedUrl;

  const StreamInfo({required this.url, this.kind = 'external', this.embedUrl});

  factory StreamInfo.fromJson(Map<String, dynamic> j) => StreamInfo(
        url: asStr(j['url']),
        kind: asStr(j['kind'], 'external'),
        embedUrl: asStrOrNull(j['embed_url']),
      );
}

/// Display-only setup metadata: venue, toss, tournament, match number.
class MatchMeta {
  final String? venue;
  final String? tournament;
  final String? matchNo;
  final String? tossWinner;
  final String? tossDecision;
  final String? tossText;

  const MatchMeta({
    this.venue,
    this.tournament,
    this.matchNo,
    this.tossWinner,
    this.tossDecision,
    this.tossText,
  });

  factory MatchMeta.fromJson(Map<String, dynamic> j) => MatchMeta(
        venue: asStrOrNull(j['venue']),
        tournament: asStrOrNull(j['tournament']),
        matchNo: asStrOrNull(j['match_no']),
        tossWinner: asStrOrNull(j['toss_winner']),
        tossDecision: asStrOrNull(j['toss_decision']),
        tossText: asStrOrNull(j['toss_text']),
      );

  bool get isEmpty =>
      venue == null &&
      tournament == null &&
      matchNo == null &&
      tossText == null;

  /// "Match 3 · City Premier League · Wankhede Ground"
  String get headline {
    final parts = <String>[
      if (matchNo != null && matchNo!.isNotEmpty) 'Match $matchNo',
      if (tournament != null && tournament!.isNotEmpty) tournament!,
      if (venue != null && venue!.isNotEmpty) venue!,
    ];
    return parts.join(' · ');
  }
}

class DlsInterruption {
  final int innings;
  final String reason;
  final double oversLost;
  final int wickets;
  final String? interruptAt;
  final String? resumeAt;
  final bool pending;

  const DlsInterruption({
    required this.innings,
    this.reason = 'rain',
    this.oversLost = 0,
    this.wickets = 0,
    this.interruptAt,
    this.resumeAt,
    this.pending = false,
  });

  factory DlsInterruption.fromJson(Map<String, dynamic> j) => DlsInterruption(
        innings: asInt(j['innings'], 1),
        reason: asStr(j['reason'], 'rain'),
        oversLost: asDouble(j['overs_lost']),
        wickets: asInt(j['wickets']),
        interruptAt: asStrOrNull(j['interrupt_at']),
        resumeAt: asStrOrNull(j['resume_at']),
        pending: asBool(j['pending']),
      );
}

/// Everything the scorer card, overlay and public page need about a rain
/// revision. Computed by the server; the scorer only confirms overs.
class DlsState {
  final bool enabled;
  final bool applied;
  final bool pending;
  final bool abandoned;
  final String? abandonReason;
  final int originalOvers;
  final int? revisedOvers;
  final int? revisedTarget;
  final int? par;
  final double r1;
  final double r2;
  final int minOvers;
  final double oversLost;
  final int revisionSeq;
  final List<DlsInterruption> interruptions;

  const DlsState({
    this.enabled = false,
    this.applied = false,
    this.pending = false,
    this.abandoned = false,
    this.abandonReason,
    this.originalOvers = 0,
    this.revisedOvers,
    this.revisedTarget,
    this.par,
    this.r1 = 0,
    this.r2 = 0,
    this.minOvers = 0,
    this.oversLost = 0,
    this.revisionSeq = 0,
    this.interruptions = const [],
  });

  factory DlsState.fromJson(Map<String, dynamic> j) => DlsState(
        enabled: asBool(j['enabled']),
        applied: asBool(j['applied']),
        pending: asBool(j['pending']),
        abandoned: asBool(j['abandoned']),
        abandonReason: asStrOrNull(j['abandon_reason']),
        originalOvers: asInt(j['original_overs']),
        revisedOvers: asIntOrNull(j['revised_overs']),
        revisedTarget: asIntOrNull(j['revised_target']),
        par: asIntOrNull(j['par']),
        r1: asDouble(j['r1']),
        r2: asDouble(j['r2']),
        minOvers: asInt(j['min_overs']),
        oversLost: asDouble(j['overs_lost']),
        revisionSeq: asInt(j['revision_seq']),
        interruptions:
            asMapList(j['interruptions']).map(DlsInterruption.fromJson).toList(),
      );

  bool get hasSummary => applied || revisedTarget != null;
}

/// A DLS target suggestion from `POST /matches/{id}/dls-suggest`.
class DlsSuggestion {
  final int target;
  final int par;
  final double r1;
  final double r2;
  final double resourcesUsed;
  final double oversLeft;
  final String note;

  const DlsSuggestion({
    this.target = 0,
    this.par = 0,
    this.r1 = 0,
    this.r2 = 0,
    this.resourcesUsed = 0,
    this.oversLeft = 0,
    this.note = '',
  });

  factory DlsSuggestion.fromJson(Map<String, dynamic> j) => DlsSuggestion(
        target: asInt(j['target']),
        par: asInt(j['par']),
        r1: asDouble(j['r1']),
        r2: asDouble(j['r2']),
        resourcesUsed: asDouble(j['resources_used']),
        oversLeft: asDouble(j['overs_left']),
        note: asStr(j['note']),
      );
}

/// The full state of a match — every mutating scoring call returns one of these.
class MatchState {
  final String id;
  final String teamA;
  final String teamB;

  /// The team NAME batting first (the server resolves the a/b choice).
  final String batFirst;
  final String formatId;
  final String rulesName;
  final MatchRules rules;
  final int currentInnings;
  final bool awaitingBowler;

  /// Between overs: a bowler can still be chosen or changed.
  final bool overPending;

  /// Bowler picked for the new over but not yet bowling.
  final String? stagedBowler;
  final List<String> availableBowlers;
  final bool canStartSecondInnings;
  final bool needsSuperOver;
  final bool awaitingSuperSecond;
  final String? result;
  final List<Innings> innings;
  final MatchAwards? awards;
  final StreamInfo? stream;
  final List<MatchClip> clips;
  final MatchMeta meta;
  final DlsState? dls;

  const MatchState({
    required this.id,
    this.teamA = '',
    this.teamB = '',
    this.batFirst = '',
    this.formatId = '',
    this.rulesName = '',
    this.rules = const MatchRules(),
    this.currentInnings = 1,
    this.awaitingBowler = false,
    this.overPending = false,
    this.stagedBowler,
    this.availableBowlers = const [],
    this.canStartSecondInnings = false,
    this.needsSuperOver = false,
    this.awaitingSuperSecond = false,
    this.result,
    this.innings = const [],
    this.awards,
    this.stream,
    this.clips = const [],
    this.meta = const MatchMeta(),
    this.dls,
  });

  factory MatchState.fromJson(Map<String, dynamic> j) => MatchState(
        id: asStr(j['id']),
        teamA: asStr(j['team_a']),
        teamB: asStr(j['team_b']),
        batFirst: asStr(j['bat_first']),
        formatId: asStr(j['format_id']),
        rulesName: asStr(j['rules_name']),
        rules: MatchRules.fromJson(asMap(j['rules'])),
        currentInnings: asInt(j['current_innings'], 1),
        awaitingBowler: asBool(j['awaiting_bowler']),
        overPending: asBool(j['over_pending']),
        stagedBowler: asStrOrNull(j['staged_bowler']),
        availableBowlers: asStrList(j['available_bowlers']),
        canStartSecondInnings: asBool(j['can_start_second_innings']),
        needsSuperOver: asBool(j['needs_super_over']),
        awaitingSuperSecond: asBool(j['awaiting_super_second']),
        result: asStrOrNull(j['result']),
        innings: asMapList(j['innings']).map(Innings.fromJson).toList(),
        awards: j['awards'] is Map
            ? MatchAwards.fromJson(asMap(j['awards']))
            : null,
        stream: j['stream'] is Map
            ? StreamInfo.fromJson(asMap(j['stream']))
            : null,
        clips: asMapList(j['clips']).map(MatchClip.fromJson).toList(),
        meta: MatchMeta.fromJson(asMap(j['meta'])),
        dls: j['dls'] is Map ? DlsState.fromJson(asMap(j['dls'])) : null,
      );

  /// The innings currently being scored, or null before anything starts.
  Innings? get current {
    final idx = currentInnings - 1;
    if (idx < 0 || idx >= innings.length) {
      return innings.isEmpty ? null : innings.last;
    }
    return innings[idx];
  }

  bool get isLive => result == null;
  bool get isComplete => result != null;

  /// The two main innings, excluding super-over rounds.
  List<Innings> get mainInnings =>
      innings.where((i) => !i.isSuperOver).take(2).toList();

  List<Innings> get superOvers => innings.where((i) => i.isSuperOver).toList();

  /// "Mumbai Strikers v Chennai Kings"
  String get title => '$teamA v $teamB';

  /// Whether the pad should offer the "start 2nd innings" action.
  bool get showSecondInningsAction =>
      canStartSecondInnings && result == null && !needsSuperOver;
}

/// A row in `GET /matches`.
class MatchSummary {
  final String id;
  final String teamA;
  final String teamB;

  /// in_progress | complete
  final String status;
  final String? result;

  const MatchSummary({
    required this.id,
    this.teamA = '',
    this.teamB = '',
    this.status = 'in_progress',
    this.result,
  });

  factory MatchSummary.fromJson(Map<String, dynamic> j) => MatchSummary(
        id: asStr(j['id']),
        teamA: asStr(j['team_a']),
        teamB: asStr(j['team_b']),
        status: asStr(j['status'], 'in_progress'),
        result: asStrOrNull(j['result']),
      );

  bool get isLive => status != 'complete';
  String get title => '$teamA v $teamB';
  String get subtitle => result ?? 'In progress';
}

/// One auto-generated ball-by-ball line.
class BallFeedItem {
  final String innings;
  final String overBall;

  /// dot | run | four | six | wide | noball | bye | legbye | wicket
  final String kind;
  final int runs;
  final String bowler;
  final String striker;
  final String text;

  /// Index of this delivery WITHIN ITS INNINGS — pass to edit/delete.
  final int idx;

  /// True only for the live innings.
  final bool editable;

  /// Whether THIS delivery was a free hit. The innings-level flag describes the
  /// NEXT ball, so correcting an earlier delivery has to use this one or the
  /// sheet offers a dismissal the engine will silently drop.
  final bool freeHit;

  const BallFeedItem({
    this.innings = '',
    this.overBall = '',
    this.kind = 'dot',
    this.runs = 0,
    this.bowler = '',
    this.striker = '',
    this.text = '',
    this.idx = 0,
    this.editable = false,
    this.freeHit = false,
  });

  factory BallFeedItem.fromJson(Map<String, dynamic> j) => BallFeedItem(
        innings: asStr(j['innings']),
        overBall: asStr(j['over_ball']),
        kind: asStr(j['kind'], 'dot'),
        runs: asInt(j['runs']),
        bowler: asStr(j['bowler']),
        striker: asStr(j['striker']),
        text: asStr(j['text']),
        idx: asInt(j['idx']),
        editable: asBool(j['editable']),
        freeHit: asBool(j['free_hit']),
      );

  /// The over number this delivery belongs to, for grouping the feed.
  int get overNumber {
    final dot = overBall.indexOf('.');
    if (dot <= 0) return 0;
    return int.tryParse(overBall.substring(0, dot)) ?? 0;
  }

  /// Short badge text: W, 4, 6, wd, nb, b, lb, or a dot.
  String get badge => switch (kind) {
        'wicket' => 'W',
        'four' => '4',
        'six' => '6',
        'wide' => 'wd',
        'noball' => 'nb',
        'bye' => 'b',
        'legbye' => 'lb',
        'run' => '$runs',
        _ => '•',
      };
}

/// One auto-generated highlight moment from the ball log (no video).
class HighlightMoment {
  final String innings;
  final String overBall;

  /// wicket | six | four | fifty | hundred | bowling | innings | dls | result
  final String kind;
  final String title;
  final String text;
  final String? team;
  final int importance;
  final double? ts;

  const HighlightMoment({
    this.innings = '',
    this.overBall = '',
    this.kind = '',
    this.title = '',
    this.text = '',
    this.team,
    this.importance = 1,
    this.ts,
  });

  factory HighlightMoment.fromJson(Map<String, dynamic> j) => HighlightMoment(
        innings: asStr(j['innings']),
        overBall: asStr(j['over_ball']),
        kind: asStr(j['kind']),
        title: asStr(j['title']),
        text: asStr(j['text']),
        team: asStrOrNull(j['team']),
        importance: asInt(j['importance'], 1),
        ts: asDoubleOrNull(j['ts']),
      );

  bool get isWicket => kind == 'wicket' || kind == 'bowling';
  bool get isBoundary => kind == 'six' || kind == 'four';
}

/// One match's clips, for the cross-match highlights gallery.
class MatchHighlightGroup {
  final String matchId;
  final String teamA;
  final String teamB;
  final bool live;
  final String statusLabel;
  final String fmt;
  final List<MatchClip> clips;

  const MatchHighlightGroup({
    required this.matchId,
    this.teamA = '',
    this.teamB = '',
    this.live = false,
    this.statusLabel = '',
    this.fmt = '',
    this.clips = const [],
  });

  factory MatchHighlightGroup.fromJson(Map<String, dynamic> j) =>
      MatchHighlightGroup(
        matchId: asStr(j['match_id']),
        teamA: asStr(j['team_a']),
        teamB: asStr(j['team_b']),
        live: asBool(j['live']),
        statusLabel: asStr(j['status_label']),
        fmt: asStr(j['fmt']),
        clips: asMapList(j['clips']).map(MatchClip.fromJson).toList(),
      );

  String get title => '$teamA vs $teamB';
}

class CommentaryNote {
  final String id;
  final String authorName;
  final String text;
  final String when;

  const CommentaryNote({
    required this.id,
    this.authorName = '',
    this.text = '',
    this.when = '',
  });

  factory CommentaryNote.fromJson(Map<String, dynamic> j) => CommentaryNote(
        id: asStr(j['id']),
        authorName: asStr(j['author_name']),
        text: asStr(j['text']),
        when: asStr(j['when']),
      );
}

/// Dropped catches, runs saved, misfields.
class FieldingEvent {
  final String id;
  final String matchId;
  final int innings;
  final String fielder;

  /// drop | save | misfield
  final String kind;
  final int runs;
  final String? bowler;
  final String? batter;
  final String? note;
  final String? overBall;
  final String when;

  const FieldingEvent({
    required this.id,
    this.matchId = '',
    this.innings = 1,
    this.fielder = '',
    this.kind = 'drop',
    this.runs = 0,
    this.bowler,
    this.batter,
    this.note,
    this.overBall,
    this.when = '',
  });

  factory FieldingEvent.fromJson(Map<String, dynamic> j) => FieldingEvent(
        id: asStr(j['id']),
        matchId: asStr(j['match_id']),
        innings: asInt(j['innings'], 1),
        fielder: asStr(j['fielder']),
        kind: asStr(j['kind'], 'drop'),
        runs: asInt(j['runs']),
        bowler: asStrOrNull(j['bowler']),
        batter: asStrOrNull(j['batter']),
        note: asStrOrNull(j['note']),
        overBall: asStrOrNull(j['over_ball']),
        when: asStr(j['when']),
      );

  static const kinds = <String>['drop', 'save', 'misfield'];

  static String kindLabel(String k) => switch (k) {
        'drop' => 'Dropped catch',
        'save' => 'Runs saved',
        _ => 'Misfield',
      };

  /// "Rohit Sharma dropped a catch" / "saved 2"
  String get summary => switch (kind) {
        'drop' => '$fielder dropped a catch',
        'save' => '$fielder saved $runs',
        _ => '$fielder misfielded${runs > 0 ? ' ($runs)' : ''}',
      };
}

/// Per-match umpire approval state from `GET /matches/{id}/officials`.
class MatchOfficials {
  final bool canScore;
  final bool isManager;

  /// none | pending | approved
  final String myStatus;
  final List<OfficialEntry> officials;

  const MatchOfficials({
    this.canScore = false,
    this.isManager = false,
    this.myStatus = 'none',
    this.officials = const [],
  });

  factory MatchOfficials.fromJson(Map<String, dynamic> j) => MatchOfficials(
        canScore: asBool(j['can_score']),
        isManager: asBool(j['is_manager']),
        myStatus: asStr(j['my_status'], 'none'),
        officials: asMapList(j['officials']).map(OfficialEntry.fromJson).toList(),
      );
}

class OfficialEntry {
  final String umpireId;
  final String umpireName;

  /// pending | approved
  final String status;

  const OfficialEntry({
    required this.umpireId,
    this.umpireName = '',
    this.status = 'pending',
  });

  factory OfficialEntry.fromJson(Map<String, dynamic> j) => OfficialEntry(
        umpireId: asStr(j['umpire_id']),
        umpireName: asStr(j['umpire_name']),
        status: asStr(j['status'], 'pending'),
      );

  bool get isApproved => status == 'approved';
}

/// A row from `GET /matches/officials/pending` — someone asking to officiate
/// a match you manage.
class PendingOfficialRequest {
  final String matchId;
  final String umpireId;
  final String umpireName;
  final String matchLabel;

  const PendingOfficialRequest({
    required this.matchId,
    required this.umpireId,
    this.umpireName = '',
    this.matchLabel = '',
  });

  factory PendingOfficialRequest.fromJson(Map<String, dynamic> j) =>
      PendingOfficialRequest(
        matchId: asStr(j['match_id']),
        umpireId: asStr(j['umpire_id']),
        umpireName: asStr(j['umpire_name']),
        matchLabel: asStr(j['match_label']),
      );
}

/// Everyone who could be fielding, for the catcher and run-out dropdowns.
///
/// `availableBowlers` is deliberately NOT this list: the server prunes it to
/// bowlers eligible for the next over, so a bowler who has finished his quota
/// would vanish and could never be credited with a catch.
List<String> fieldingSideNames(MatchState match) {
  final current = match.current;
  if (current == null) return const [];

  // Whoever is bowling now is the fielding side. Their names appear as the
  // bowlers of this innings and as the batters of the other one.
  final fieldingTeam = current.bowlingTeam;
  final names = <String>{...match.availableBowlers};

  for (final innings in match.innings) {
    if (innings.bowlingTeam == fieldingTeam) {
      for (final b in innings.bowlers) {
        names.add(b.name);
      }
    }
    if (innings.battingTeam == fieldingTeam) {
      for (final b in innings.batters) {
        if (b.hasBatted) names.add(b.name);
      }
    }
  }

  return names.where((n) => n.isNotEmpty).toList()..sort();
}

/// The body of a `POST /matches/{id}/balls` call.
class BallRequest {
  /// runs | wide | no_ball | bye | leg_bye | wicket
  final String action;
  final int value;
  final String? dismissal;

  /// striker | non_striker
  final String batterOut;
  final String? fielder;
  final double? wagonX;
  final double? wagonY;
  final double? pitchX;
  final double? pitchY;
  final double? speed;

  const BallRequest({
    required this.action,
    this.value = 0,
    this.dismissal,
    this.batterOut = 'striker',
    this.fielder,
    this.wagonX,
    this.wagonY,
    this.pitchX,
    this.pitchY,
    this.speed,
  });

  static const actionRuns = 'runs';
  static const actionWide = 'wide';
  static const actionNoBall = 'no_ball';
  static const actionBye = 'bye';
  static const actionLegBye = 'leg_bye';
  static const actionWicket = 'wicket';

  BallRequest copyWith({
    double? wagonX,
    double? wagonY,
    double? pitchX,
    double? pitchY,
    int? value,
    String? dismissal,
    String? batterOut,
    String? fielder,
  }) =>
      BallRequest(
        action: action,
        value: value ?? this.value,
        dismissal: dismissal ?? this.dismissal,
        batterOut: batterOut ?? this.batterOut,
        fielder: fielder ?? this.fielder,
        wagonX: wagonX ?? this.wagonX,
        wagonY: wagonY ?? this.wagonY,
        pitchX: pitchX ?? this.pitchX,
        pitchY: pitchY ?? this.pitchY,
        speed: speed,
      );

  Map<String, dynamic> toJson() => {
        'action': action,
        'value': value,
        if (dismissal != null) 'dismissal': dismissal,
        'batter_out': batterOut,
        if (fielder != null && fielder!.isNotEmpty) 'fielder': fielder,
        if (wagonX != null) 'wagon_x': wagonX,
        if (wagonY != null) 'wagon_y': wagonY,
        if (pitchX != null) 'pitch_x': pitchX,
        if (pitchY != null) 'pitch_y': pitchY,
        if (speed != null) 'speed': speed,
      };

  /// Did the batter actually hit this one? Drives the wagon-wheel prompt.
  bool get isBatShot {
    if (action == actionRuns) return value > 0;
    if (action == actionNoBall) return value > 0;
    if (action == actionWicket) {
      return dismissal == Dismissals.caught ||
          dismissal == Dismissals.caughtBehind ||
          dismissal == Dismissals.caughtAndBowled ||
          dismissal == Dismissals.boundaryOut;
    }
    return false;
  }
}
