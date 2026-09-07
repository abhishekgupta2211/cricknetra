/// Full-fidelity mirror of `backend/app/domain/rules.py :: MatchRules`.
///
/// Every field round-trips, so a rulebook fetched from `/presets/{id}` can be
/// edited in the rule builder and posted straight back inside `POST /matches`
/// without silently dropping anything the server cares about.
library;

import 'json.dart';

/// Every dismissal kind the engine understands.
class Dismissals {
  const Dismissals._();

  static const bowled = 'bowled';
  static const caught = 'caught';
  static const caughtBehind = 'caught_behind';
  static const caughtAndBowled = 'caught_and_bowled';
  static const lbw = 'lbw';
  static const runOut = 'run_out';
  static const stumped = 'stumped';
  static const hitWicket = 'hit_wicket';
  static const retiredHurt = 'retired_hurt';
  static const retiredOut = 'retired_out';
  static const obstructingField = 'obstructing_field';
  static const hitBallTwice = 'hit_ball_twice';
  static const timedOut = 'timed_out';
  static const boundaryOut = 'boundary_out';

  /// The default "everything allowed" set. `boundary_out` is excluded because it
  /// is format-specific, gated by [MatchRules.overBoundaryOut].
  static const standard = <String>[
    bowled,
    caught,
    caughtBehind,
    caughtAndBowled,
    lbw,
    runOut,
    stumped,
    hitWicket,
    retiredHurt,
    retiredOut,
    obstructingField,
    hitBallTwice,
    timedOut,
  ];

  /// On a free hit a batter can only go these ways.
  static const onFreeHit = <String>{runOut, obstructingField, hitBallTwice};

  /// Dismissals where naming the fielder makes sense.
  static const needsFielder = <String>{caught, caughtBehind, runOut, stumped};

  /// Dismissals where the batters can have completed runs before the ball was
  /// dead. Everywhere else the ball is dead at once, and the engine would still
  /// credit any runs sent with it to the striker — so the picker must not
  /// appear. Retirements are excluded because the striker who is credited need
  /// not be the batter leaving, and a double hit scores no runs off the bat.
  static const canCompleteRuns = <String>{runOut, obstructingField};

  /// Dismissals credited to the bowler.
  static const creditedToBowler = <String>{
    bowled,
    caught,
    caughtBehind,
    caughtAndBowled,
    lbw,
    stumped,
    hitWicket,
    boundaryOut,
  };

  /// Retired hurt leaves the batter not out.
  static bool isNotOut(String kind) => kind == retiredHurt;

  static const _labels = <String, String>{
    bowled: 'Bowled',
    caught: 'Caught',
    caughtBehind: 'Caught behind',
    caughtAndBowled: 'Caught & bowled',
    lbw: 'LBW',
    runOut: 'Run out',
    stumped: 'Stumped',
    hitWicket: 'Hit wicket',
    retiredHurt: 'Retired hurt',
    retiredOut: 'Retired out',
    obstructingField: 'Obstructing the field',
    hitBallTwice: 'Hit the ball twice',
    timedOut: 'Timed out',
    boundaryOut: 'Boundary out',
  };

  static String label(String kind) =>
      _labels[kind] ?? kind.replaceAll('_', ' ');
}

/// Physical ball used, which segments a player's career splits.
class BallTypes {
  const BallTypes._();
  static const leather = 'leather';
  static const tennis = 'tennis';
  static const other = 'other';
  static const all = <String>[leather, tennis, other];
  static String label(String v) => switch (v) {
        leather => 'Leather',
        tennis => 'Tennis',
        _ => 'Other',
      };
}

/// An inclusive, 1-based range of overs with a fielding restriction.
class PowerplayRange {
  final int startOver;
  final int endOver;
  final int maxFieldersOutside;
  final String label;

  const PowerplayRange({
    required this.startOver,
    required this.endOver,
    this.maxFieldersOutside = 2,
    this.label = 'Powerplay',
  });

  factory PowerplayRange.fromJson(Map<String, dynamic> j) => PowerplayRange(
        startOver: asInt(j['start_over'], 1),
        endOver: asInt(j['end_over'], 1),
        maxFieldersOutside: asInt(j['max_fielders_outside'], 2),
        label: asStr(j['label'], 'Powerplay'),
      );

  Map<String, dynamic> toJson() => {
        'start_over': startOver,
        'end_over': endOver,
        'max_fielders_outside': maxFieldersOutside,
        'label': label,
      };

  PowerplayRange copyWith({
    int? startOver,
    int? endOver,
    int? maxFieldersOutside,
    String? label,
  }) =>
      PowerplayRange(
        startOver: startOver ?? this.startOver,
        endOver: endOver ?? this.endOver,
        maxFieldersOutside: maxFieldersOutside ?? this.maxFieldersOutside,
        label: label ?? this.label,
      );

  bool covers(int overNumber) =>
      overNumber >= startOver && overNumber <= endOver;
}

class WideRules {
  final bool enabled;
  final int runPenalty;

  /// `false` means the delivery is re-bowled (it does not advance the over).
  final bool countsAsLegalBall;
  final bool allowByes;

  const WideRules({
    this.enabled = true,
    this.runPenalty = 1,
    this.countsAsLegalBall = false,
    this.allowByes = true,
  });

  factory WideRules.fromJson(Map<String, dynamic> j) => WideRules(
        enabled: asBool(j['enabled'], true),
        runPenalty: asInt(j['run_penalty'], 1),
        countsAsLegalBall: asBool(j['counts_as_legal_ball']),
        allowByes: asBool(j['allow_byes'], true),
      );

  Map<String, dynamic> toJson() => {
        'enabled': enabled,
        'run_penalty': runPenalty,
        'counts_as_legal_ball': countsAsLegalBall,
        'allow_byes': allowByes,
      };

  WideRules copyWith({
    bool? enabled,
    int? runPenalty,
    bool? countsAsLegalBall,
    bool? allowByes,
  }) =>
      WideRules(
        enabled: enabled ?? this.enabled,
        runPenalty: runPenalty ?? this.runPenalty,
        countsAsLegalBall: countsAsLegalBall ?? this.countsAsLegalBall,
        allowByes: allowByes ?? this.allowByes,
      );
}

class NoBallRules {
  final bool enabled;
  final int runPenalty;
  final bool countsAsLegalBall;

  /// The next legal delivery is a free hit.
  final bool freeHit;

  /// Runs hit off a no-ball are credited to the batter.
  final bool offBatCounts;
  final bool allowByes;

  const NoBallRules({
    this.enabled = true,
    this.runPenalty = 1,
    this.countsAsLegalBall = false,
    this.freeHit = true,
    this.offBatCounts = true,
    this.allowByes = true,
  });

  factory NoBallRules.fromJson(Map<String, dynamic> j) => NoBallRules(
        enabled: asBool(j['enabled'], true),
        runPenalty: asInt(j['run_penalty'], 1),
        countsAsLegalBall: asBool(j['counts_as_legal_ball']),
        freeHit: asBool(j['free_hit'], true),
        offBatCounts: asBool(j['off_bat_counts'], true),
        allowByes: asBool(j['allow_byes'], true),
      );

  Map<String, dynamic> toJson() => {
        'enabled': enabled,
        'run_penalty': runPenalty,
        'counts_as_legal_ball': countsAsLegalBall,
        'free_hit': freeHit,
        'off_bat_counts': offBatCounts,
        'allow_byes': allowByes,
      };

  NoBallRules copyWith({
    bool? enabled,
    int? runPenalty,
    bool? countsAsLegalBall,
    bool? freeHit,
    bool? offBatCounts,
    bool? allowByes,
  }) =>
      NoBallRules(
        enabled: enabled ?? this.enabled,
        runPenalty: runPenalty ?? this.runPenalty,
        countsAsLegalBall: countsAsLegalBall ?? this.countsAsLegalBall,
        freeHit: freeHit ?? this.freeHit,
        offBatCounts: offBatCounts ?? this.offBatCounts,
        allowByes: allowByes ?? this.allowByes,
      );
}

/// One stoppage in play. The server maintains these; the client only displays
/// them and echoes them back untouched.
class Interruption {
  final int innings;
  final String reason;
  final int balls;
  final int wickets;
  final double oversBefore;
  final double oversAfter;
  final String? interruptAt;
  final String? resumeAt;
  final bool pending;

  const Interruption({
    required this.innings,
    this.reason = 'rain',
    this.balls = 0,
    this.wickets = 0,
    this.oversBefore = 0,
    this.oversAfter = 0,
    this.interruptAt,
    this.resumeAt,
    this.pending = false,
  });

  factory Interruption.fromJson(Map<String, dynamic> j) => Interruption(
        innings: asInt(j['innings'], 1),
        reason: asStr(j['reason'], 'rain'),
        balls: asInt(j['balls']),
        wickets: asInt(j['wickets']),
        oversBefore: asDouble(j['overs_before']),
        oversAfter: asDouble(j['overs_after']),
        interruptAt: asStrOrNull(j['interrupt_at']),
        resumeAt: asStrOrNull(j['resume_at']),
        pending: asBool(j['pending']),
      );

  Map<String, dynamic> toJson() => {
        'innings': innings,
        'reason': reason,
        'balls': balls,
        'wickets': wickets,
        'overs_before': oversBefore,
        'overs_after': oversAfter,
        'interrupt_at': interruptAt,
        'resume_at': resumeAt,
        'pending': pending,
      };

  double get oversLost {
    final lost = oversBefore - oversAfter;
    return lost <= 0 ? 0 : double.parse(lost.toStringAsFixed(2));
  }
}

/// Reasons play can stop, matching the server's validation pattern.
class StoppageReasons {
  const StoppageReasons._();
  static const all = <String>[
    'rain',
    'bad_light',
    'wet_outfield',
    'ground_delay',
    'power_failure',
    'other',
  ];

  static String label(String v) => switch (v) {
        'rain' => 'Rain',
        'bad_light' => 'Bad light',
        'wet_outfield' => 'Wet outfield',
        'ground_delay' => 'Ground delay',
        'power_failure' => 'Power failure',
        _ => 'Other',
      };
}

/// Persisted setup for one super-over round.
class SuperOverRound {
  final String batFirst;
  final bool secondStarted;

  const SuperOverRound({required this.batFirst, this.secondStarted = false});

  factory SuperOverRound.fromJson(Map<String, dynamic> j) => SuperOverRound(
        batFirst: asStr(j['bat_first']),
        secondStarted: asBool(j['second_started']),
      );

  Map<String, dynamic> toJson() =>
      {'bat_first': batFirst, 'second_started': secondStarted};
}

/// A complete, self-contained description of how a match is scored.
class MatchRules {
  final String name;
  final String formatId;
  final String description;

  // ---- Shape of the contest ----
  final int playersPerSide;
  final int oversPerInnings;
  final int ballsPerOver;
  final int inningsPerSide;
  final String ballType;

  // ---- Bowling constraints ----
  final int? maxOversPerBowler;
  final bool allowConsecutiveOvers;

  // ---- Fielding restrictions ----
  final List<PowerplayRange> powerplays;
  final int defaultFieldersOutside;

  // ---- Extras ----
  final WideRules wide;
  final NoBallRules noBall;
  final bool byesAllowed;
  final bool legByesAllowed;

  // ---- Format quirks ----
  final bool lastManStands;
  final bool allowDeclaration;
  final bool superOverOnTie;
  final bool dlsEnabled;

  // ---- Per-match state the server owns (echoed back unchanged) ----
  final int? revisedTarget;
  final int? revisedOvers;
  final List<Interruption> interruptions;
  final bool abandoned;
  final String? abandonReason;
  final int dlsMinOvers;
  final int g50;
  final int? declaredInnings;
  final List<SuperOverRound> superOverRounds;

  /// Hitting the ball over the boundary on the full is OUT, not six.
  final bool overBoundaryOut;

  final List<String> allowedDismissals;
  final int fourValue;
  final int sixValue;

  const MatchRules({
    this.name = 'Custom',
    this.formatId = 'custom',
    this.description = '',
    this.playersPerSide = 11,
    this.oversPerInnings = 20,
    this.ballsPerOver = 6,
    this.inningsPerSide = 1,
    this.ballType = BallTypes.leather,
    this.maxOversPerBowler,
    this.allowConsecutiveOvers = false,
    this.powerplays = const [],
    this.defaultFieldersOutside = 5,
    this.wide = const WideRules(),
    this.noBall = const NoBallRules(),
    this.byesAllowed = true,
    this.legByesAllowed = true,
    this.lastManStands = false,
    this.allowDeclaration = false,
    this.superOverOnTie = false,
    this.dlsEnabled = false,
    this.revisedTarget,
    this.revisedOvers,
    this.interruptions = const [],
    this.abandoned = false,
    this.abandonReason,
    this.dlsMinOvers = 0,
    this.g50 = 245,
    this.declaredInnings,
    this.superOverRounds = const [],
    this.overBoundaryOut = false,
    this.allowedDismissals = Dismissals.standard,
    this.fourValue = 4,
    this.sixValue = 6,
  });

  factory MatchRules.fromJson(Map<String, dynamic> j) => MatchRules(
        name: asStr(j['name'], 'Custom'),
        formatId: asStr(j['format_id'], 'custom'),
        description: asStr(j['description']),
        playersPerSide: asInt(j['players_per_side'], 11),
        oversPerInnings: asInt(j['overs_per_innings'], 20),
        ballsPerOver: asInt(j['balls_per_over'], 6),
        inningsPerSide: asInt(j['innings_per_side'], 1),
        ballType: asStr(j['ball_type'], BallTypes.leather),
        maxOversPerBowler: asIntOrNull(j['max_overs_per_bowler']),
        allowConsecutiveOvers: asBool(j['allow_consecutive_overs']),
        powerplays:
            asMapList(j['powerplays']).map(PowerplayRange.fromJson).toList(),
        defaultFieldersOutside: asInt(j['default_fielders_outside'], 5),
        wide: WideRules.fromJson(asMap(j['wide'])),
        noBall: NoBallRules.fromJson(asMap(j['no_ball'])),
        byesAllowed: asBool(j['byes_allowed'], true),
        legByesAllowed: asBool(j['leg_byes_allowed'], true),
        lastManStands: asBool(j['last_man_stands']),
        allowDeclaration: asBool(j['allow_declaration']),
        superOverOnTie: asBool(j['super_over_on_tie']),
        dlsEnabled: asBool(j['dls_enabled']),
        revisedTarget: asIntOrNull(j['revised_target']),
        revisedOvers: asIntOrNull(j['revised_overs']),
        interruptions:
            asMapList(j['interruptions']).map(Interruption.fromJson).toList(),
        abandoned: asBool(j['abandoned']),
        abandonReason: asStrOrNull(j['abandon_reason']),
        dlsMinOvers: asInt(j['dls_min_overs']),
        g50: asInt(j['g50'], 245),
        declaredInnings: asIntOrNull(j['declared_innings']),
        superOverRounds: asMapList(j['super_over_rounds'])
            .map(SuperOverRound.fromJson)
            .toList(),
        overBoundaryOut: asBool(j['over_boundary_out']),
        allowedDismissals: j['allowed_dismissals'] is List
            ? asStrList(j['allowed_dismissals'])
            : Dismissals.standard,
        fourValue: asInt(j['four_value'], 4),
        sixValue: asInt(j['six_value'], 6),
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        'format_id': formatId,
        'description': description,
        'players_per_side': playersPerSide,
        'overs_per_innings': oversPerInnings,
        'balls_per_over': ballsPerOver,
        'innings_per_side': inningsPerSide,
        'ball_type': ballType,
        'max_overs_per_bowler': maxOversPerBowler,
        'allow_consecutive_overs': allowConsecutiveOvers,
        'powerplays': powerplays.map((p) => p.toJson()).toList(),
        'default_fielders_outside': defaultFieldersOutside,
        'wide': wide.toJson(),
        'no_ball': noBall.toJson(),
        'byes_allowed': byesAllowed,
        'leg_byes_allowed': legByesAllowed,
        'last_man_stands': lastManStands,
        'allow_declaration': allowDeclaration,
        'super_over_on_tie': superOverOnTie,
        'dls_enabled': dlsEnabled,
        'revised_target': revisedTarget,
        'revised_overs': revisedOvers,
        'interruptions': interruptions.map((e) => e.toJson()).toList(),
        'abandoned': abandoned,
        'abandon_reason': abandonReason,
        'dls_min_overs': dlsMinOvers,
        'g50': g50,
        'declared_innings': declaredInnings,
        'super_over_rounds': superOverRounds.map((e) => e.toJson()).toList(),
        'over_boundary_out': overBoundaryOut,
        'allowed_dismissals': allowedDismissals,
        'four_value': fourValue,
        'six_value': sixValue,
      };

  MatchRules copyWith({
    String? name,
    String? formatId,
    String? description,
    int? playersPerSide,
    int? oversPerInnings,
    int? ballsPerOver,
    int? inningsPerSide,
    String? ballType,
    int? maxOversPerBowler,
    bool clearMaxOversPerBowler = false,
    bool? allowConsecutiveOvers,
    List<PowerplayRange>? powerplays,
    int? defaultFieldersOutside,
    WideRules? wide,
    NoBallRules? noBall,
    bool? byesAllowed,
    bool? legByesAllowed,
    bool? lastManStands,
    bool? allowDeclaration,
    bool? superOverOnTie,
    bool? dlsEnabled,
    int? dlsMinOvers,
    int? g50,
    bool? overBoundaryOut,
    List<String>? allowedDismissals,
    int? fourValue,
    int? sixValue,
  }) =>
      MatchRules(
        name: name ?? this.name,
        formatId: formatId ?? this.formatId,
        description: description ?? this.description,
        playersPerSide: playersPerSide ?? this.playersPerSide,
        oversPerInnings: oversPerInnings ?? this.oversPerInnings,
        ballsPerOver: ballsPerOver ?? this.ballsPerOver,
        inningsPerSide: inningsPerSide ?? this.inningsPerSide,
        ballType: ballType ?? this.ballType,
        maxOversPerBowler: clearMaxOversPerBowler
            ? null
            : (maxOversPerBowler ?? this.maxOversPerBowler),
        allowConsecutiveOvers:
            allowConsecutiveOvers ?? this.allowConsecutiveOvers,
        powerplays: powerplays ?? this.powerplays,
        defaultFieldersOutside:
            defaultFieldersOutside ?? this.defaultFieldersOutside,
        wide: wide ?? this.wide,
        noBall: noBall ?? this.noBall,
        byesAllowed: byesAllowed ?? this.byesAllowed,
        legByesAllowed: legByesAllowed ?? this.legByesAllowed,
        lastManStands: lastManStands ?? this.lastManStands,
        allowDeclaration: allowDeclaration ?? this.allowDeclaration,
        superOverOnTie: superOverOnTie ?? this.superOverOnTie,
        dlsEnabled: dlsEnabled ?? this.dlsEnabled,
        revisedTarget: revisedTarget,
        revisedOvers: revisedOvers,
        interruptions: interruptions,
        abandoned: abandoned,
        abandonReason: abandonReason,
        dlsMinOvers: dlsMinOvers ?? this.dlsMinOvers,
        g50: g50 ?? this.g50,
        declaredInnings: declaredInnings,
        superOverRounds: superOverRounds,
        overBoundaryOut: overBoundaryOut ?? this.overBoundaryOut,
        allowedDismissals: allowedDismissals ?? this.allowedDismissals,
        fourValue: fourValue ?? this.fourValue,
        sixValue: sixValue ?? this.sixValue,
      );

  /// How many wickets end the innings. Normally players-1 (the last batter has
  /// no partner); with last-man-stands the final batter continues alone.
  int get wicketsToAllOut =>
      lastManStands ? playersPerSide : playersPerSide - 1;

  int get totalLegalBalls => oversPerInnings * ballsPerOver;

  bool isPowerplay(int overNumber) =>
      powerplays.any((pp) => pp.covers(overNumber));

  PowerplayRange? activePowerplay(int overNumber) {
    for (final pp in powerplays) {
      if (pp.covers(overNumber)) return pp;
    }
    return null;
  }

  int fieldersOutsideLimit(int overNumber) =>
      activePowerplay(overNumber)?.maxFieldersOutside ?? defaultFieldersOutside;

  bool dismissalAllowed(String kind) => kind == Dismissals.boundaryOut
      ? overBoundaryOut
      : allowedDismissals.contains(kind);

  /// Every dismissal the scorer may pick in this format, in a sensible order.
  List<String> get selectableDismissals => [
        ...Dismissals.standard.where(allowedDismissals.contains),
        if (overBoundaryOut) Dismissals.boundaryOut,
      ];

  /// A one-line summary for cards and pickers, e.g. "20 ov · 11-a-side · Leather".
  String get summaryLine {
    final bits = <String>[
      '$oversPerInnings ov',
      '$playersPerSide-a-side',
      BallTypes.label(ballType),
      if (ballsPerOver != 6) '$ballsPerOver balls/over',
      if (lastManStands) 'Last man stands',
      if (overBoundaryOut) 'Rule-out',
    ];
    return bits.join(' · ');
  }
}

/// A built-in format as listed by `GET /presets`.
class PresetSummary {
  final String id;
  final String name;
  final String description;
  final int playersPerSide;
  final int oversPerInnings;
  final int ballsPerOver;
  final String ballType;
  final bool lastManStands;

  const PresetSummary({
    required this.id,
    required this.name,
    this.description = '',
    this.playersPerSide = 11,
    this.oversPerInnings = 20,
    this.ballsPerOver = 6,
    this.ballType = BallTypes.leather,
    this.lastManStands = false,
  });

  factory PresetSummary.fromJson(Map<String, dynamic> j) => PresetSummary(
        id: asStr(j['id']),
        name: asStr(j['name']),
        description: asStr(j['description']),
        playersPerSide: asInt(j['players_per_side'], 11),
        oversPerInnings: asInt(j['overs_per_innings'], 20),
        ballsPerOver: asInt(j['balls_per_over'], 6),
        ballType: asStr(j['ball_type'], BallTypes.leather),
        lastManStands: asBool(j['last_man_stands']),
      );

  String get summaryLine =>
      '$oversPerInnings ov · $playersPerSide-a-side · ${BallTypes.label(ballType)}';
}
