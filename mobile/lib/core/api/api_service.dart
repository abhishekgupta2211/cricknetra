import 'dart:async';

import 'package:dio/dio.dart' show CancelToken;

import '../models/json.dart';
import '../models/match.dart';
import '../models/career.dart';
import '../models/org.dart';
import '../models/roster.dart';
import '../models/rules.dart';
import '../models/social.dart';
import '../models/tournament.dart';
import '../models/user.dart';
import 'api_client.dart';
import 'api_exception.dart';

/// The whole CricNetra API, typed.
///
/// Every screen goes through here, so no widget ever touches a raw
/// `Map<String, dynamic>` — which is what let the previous client drift out of
/// sync with the server without anything failing loudly.
class ApiService {
  final ApiClient client;

  ApiService(this.client);

  // ================================================================== auth

  /// Returns the token pair. The caller persists it.
  Future<({String accessToken, String? refreshToken})> login(
    String identifier,
    String password,
  ) async {
    final r = asMap(await client.post(
      '/auth/login',
      body: {'identifier': identifier, 'password': password},
    ));
    return (
      accessToken: asStr(r['access_token']),
      refreshToken: asStrOrNull(r['refresh_token']),
    );
  }

  Future<AppUser> register({
    required String fullName,
    required String username,
    required String mobileNo,
    required String password,
    required String role,
    String? email,
  }) async {
    final r = await client.post('/auth/register', body: {
      'full_name': fullName,
      'username': username,
      'mobile_no': mobileNo,
      'password': password,
      'role': role,
      'email': ?email,
    });
    return AppUser.fromJson(asMap(r));
  }

  Future<AppUser> me() async => AppUser.fromJson(asMap(await client.get('/auth/me')));

  Future<void> logout(String refreshToken) =>
      client.post('/auth/logout', body: {'refresh_token': refreshToken});

  Future<void> logoutAll() => client.post('/auth/logout-all');

  Future<AppUser> setEmail(String email) async =>
      AppUser.fromJson(asMap(await client.patch('/auth/email', body: {'email': email})));

  /// Requests an OTP. In dev builds the code comes back in `dev_code`.
  Future<String?> requestVerification() async {
    final r = asMap(await client.post('/auth/verify/request'));
    return asStrOrNull(r['dev_code']);
  }

  Future<void> confirmVerification(String code) =>
      client.post('/auth/verify/confirm', body: {'code': code});

  /// Starts a password reset. Dev builds return the token in `dev_token`.
  Future<String?> forgotPassword(String identifier) async {
    final r = asMap(
      await client.post('/auth/password/forgot', body: {'identifier': identifier}),
    );
    return asStrOrNull(r['dev_token']);
  }

  Future<void> resetPassword(String token, String newPassword) => client.post(
        '/auth/password/reset',
        body: {'token': token, 'new_password': newPassword},
      );

  /// Null when the profile has not been completed yet — the server answers 404
  /// for that, which is a state rather than a failure.
  Future<UserProfile?> myProfile() async {
    try {
      return UserProfile.fromJson(asMap(await client.get('/auth/profile')));
    } on ApiException catch (e) {
      if (e.isNotFound) return null;
      rethrow;
    }
  }

  Future<UserProfile> completeProfile(Map<String, dynamic> body) async =>
      UserProfile.fromJson(asMap(await client.post('/auth/profile', body: body)));

  Future<UserProfile> updateProfile(Map<String, dynamic> body) async =>
      UserProfile.fromJson(asMap(await client.patch('/auth/profile', body: body)));

  Future<void> uploadProfilePhoto(String path) =>
      client.upload('/auth/profile/photo', filePath: path);

  Future<void> deleteProfilePhoto() => client.delete('/auth/profile/photo');

  // ================================================================ people

  Future<List<PublicUser>> users({String? role}) async {
    final r = await client.get(
      '/users',
      query: role == null || role.isEmpty ? null : {'role': role},
    );
    return asMapList(r).map(PublicUser.fromJson).toList();
  }

  Future<SearchResults> search(String q) async =>
      SearchResults.fromJson(asMap(await client.get('/search', query: {'q': q})));

  // =============================================================== presets

  Future<List<PresetSummary>> presets() async =>
      asMapList(await client.get('/presets')).map(PresetSummary.fromJson).toList();

  /// The full editable rulebook behind a preset.
  Future<MatchRules> preset(String formatId) async =>
      MatchRules.fromJson(asMap(await client.get('/presets/$formatId')));

  Future<List<RuleTemplate>> ruleTemplates() async =>
      asMapList(await client.get('/rule-templates'))
          .map(RuleTemplate.fromJson)
          .toList();

  Future<RuleTemplate> ruleTemplate(String id) async =>
      RuleTemplate.fromJson(asMap(await client.get('/rule-templates/$id')));

  Future<RuleTemplate> saveRuleTemplate(MatchRules rules) async =>
      RuleTemplate.fromJson(
        asMap(await client.post('/rule-templates', body: rules.toJson())),
      );

  Future<void> deleteRuleTemplate(String id) =>
      client.delete('/rule-templates/$id');

  // =============================================================== players

  Future<List<Player>> players() async =>
      asMapList(await client.get('/players')).map(Player.fromJson).toList();

  Future<Player> player(String id) async =>
      Player.fromJson(asMap(await client.get('/players/$id')));

  Future<Player> createPlayer({
    required String name,
    String? phone,
    String? battingStyle,
    String? bowlingStyle,
  }) async =>
      Player.fromJson(asMap(await client.post('/players', body: {
        'name': name,
        'phone': ?phone,
        if (battingStyle != null && battingStyle.isNotEmpty)
          'batting_style': battingStyle,
        if (bowlingStyle != null && bowlingStyle.isNotEmpty)
          'bowling_style': bowlingStyle,
      })));

  Future<Player> updatePlayer(String id, Map<String, dynamic> body) async =>
      Player.fromJson(asMap(await client.patch('/players/$id', body: body)));

  Future<void> deletePlayer(String id) => client.delete('/players/$id');

  Future<PlayerStats> playerStats(String id) async =>
      PlayerStats.fromJson(asMap(await client.get('/players/$id/stats')));

  Future<PlayerInsights> playerInsights(String id) async =>
      PlayerInsights.fromJson(asMap(await client.get('/players/$id/insights')));

  Future<PlayerSplits> playerSplits(String id) async =>
      PlayerSplits.fromJson(asMap(await client.get('/players/$id/splits')));

  /// A player's whole career: every match with their own line in it, plus the
  /// record broken down by tournament, year and side.
  Future<PlayerHistory> playerHistory(String id) async =>
      PlayerHistory.fromJson(asMap(await client.get('/players/$id/history')));

  // ---------------------------------------------------------------- admin
  // Areas, organizations and organizers. Admin-only on the server; the app
  // hides them from everybody else as a convenience, not as the boundary.

  Future<List<Area>> areas() async =>
      asMapList(await client.get('/admin/areas')).map(Area.fromJson).toList();

  Future<Area> createArea(String name, {String? state}) async =>
      Area.fromJson(asMap(await client.post('/admin/areas', body: {
        'name': name,
        'state': ?state,
      })));

  Future<void> deleteArea(String id) => client.delete('/admin/areas/$id');

  Future<List<Organization>> organizations({String? areaId}) async =>
      asMapList(await client.get(
        '/admin/organizations',
        query: {'area_id': ?areaId},
      )).map(Organization.fromJson).toList();

  Future<Organization> createOrganization(String name, {String? areaId}) async =>
      Organization.fromJson(asMap(await client.post('/admin/organizations', body: {
        'name': name,
        'area_id': ?areaId,
      })));

  Future<void> deleteOrganization(String id) =>
      client.delete('/admin/organizations/$id');

  Future<List<Organizer>> organizers({String? areaId}) async =>
      asMapList(await client.get(
        '/admin/organizers',
        query: {'area_id': ?areaId},
      )).map(Organizer.fromJson).toList();

  /// Promote an existing account. Deliberately not a second way to create
  /// accounts: the person signs up like everybody else and the admin grants
  /// the role, so there is one password policy and one verification flow.
  Future<Organizer> createOrganizer(
    String userId, {
    String? areaId,
    String? organizationId,
  }) async =>
      Organizer.fromJson(asMap(await client.post('/admin/organizers', body: {
        'user_id': userId,
        'area_id': ?areaId,
        'organization_id': ?organizationId,
      })));

  Future<Organizer> updateOrganizer(
    String userId, {
    String? areaId,
    String? organizationId,
    bool? isActive,
  }) async =>
      Organizer.fromJson(
          asMap(await client.patch('/admin/organizers/$userId', body: {
        'area_id': ?areaId,
        'organization_id': ?organizationId,
        'is_active': ?isActive,
      })));

  /// Deactivates the profile and demotes the account. Their tournaments keep
  /// their owner so an admin can reassign or delete them deliberately.
  Future<void> removeOrganizer(String userId) =>
      client.delete('/admin/organizers/$userId');

  /// The only way a role changes.
  Future<void> assignRole(String userId, String role) =>
      client.put('/admin/users/$userId/role', body: {'role': role});

  Future<List<AuditEntry>> auditTrail({int? limit, String? action}) async =>
      asMapList(await client.get('/admin/audit', query: {
        if (limit != null) 'limit': '$limit',
        'action': ?action,
      })).map(AuditEntry.fromJson).toList();

  // ------------------------------------------------------ tournament staff

  Future<List<TournamentStaff>> tournamentStaff(
    String tournamentId, {
    String? staffRole,
  }) async =>
      asMapList(await client.get(
        '/tournaments/$tournamentId/staff',
        query: {'staff_role': ?staffRole},
      )).map(TournamentStaff.fromJson).toList();

  Future<TournamentStaff> addUmpire(String tournamentId, String userId) async =>
      TournamentStaff.fromJson(asMap(await client.post(
        '/tournaments/$tournamentId/staff/umpires',
        body: {'user_id': userId},
      )));

  Future<TournamentStaff> addCommentator(
          String tournamentId, String userId) async =>
      TournamentStaff.fromJson(asMap(await client.post(
        '/tournaments/$tournamentId/staff/commentators',
        body: {'user_id': userId},
      )));

  /// Removes them from THIS competition only — their account and their
  /// staffing on anybody else's tournament are untouched.
  Future<void> removeStaff(
          String tournamentId, String staffRole, String userId) =>
      client.delete('/tournaments/$tournamentId/staff/$staffRole/$userId');

  Future<TournamentStaff> setStaffActive(
    String tournamentId,
    String staffRole,
    String userId,
    bool isActive,
  ) async =>
      TournamentStaff.fromJson(asMap(await client.patch(
        '/tournaments/$tournamentId/staff/$staffRole/$userId',
        body: {'is_active': isActive},
      )));

  /// The competitions the signed-in user is staff on. The server reads the
  /// caller from the token; there is no user parameter to tamper with.
  Future<List<MyStaffing>> myStaffing() async =>
      asMapList(await client.get('/tournaments/mine/staffing'))
          .map(MyStaffing.fromJson)
          .toList();

  Future<List<TournamentPlayer>> tournamentPlayers(String tournamentId) async =>
      asMapList(await client.get('/tournaments/$tournamentId/players'))
          .map(TournamentPlayer.fromJson)
          .toList();

  Future<List<PlayerAward>> playerAwards(String id) async =>
      asMapList(await client.get('/players/$id/awards'))
          .map(PlayerAward.fromJson)
          .toList();

  Future<List<Player>> claimablePlayers() async =>
      asMapList(await client.get('/players/claimable'))
          .map(Player.fromJson)
          .toList();

  Future<List<Player>> myPlayers() async =>
      asMapList(await client.get('/players/mine')).map(Player.fromJson).toList();

  Future<Player> claimPlayer(String id) async =>
      Player.fromJson(asMap(await client.post('/players/$id/claim')));

  Future<void> uploadPlayerPhoto(String id, String path) =>
      client.upload('/players/$id/photo', filePath: path);

  Future<void> deletePlayerPhoto(String id) =>
      client.delete('/players/$id/photo');

  Future<PlayerCompare> comparePlayers(String a, String b) async =>
      PlayerCompare.fromJson(asMap(await client.get(
        '/insights/compare',
        query: {'player_a': a, 'player_b': b},
      )));

  // ================================================================= teams

  Future<List<Team>> teams() async =>
      asMapList(await client.get('/teams')).map(Team.fromJson).toList();

  Future<Team> team(String id) async =>
      Team.fromJson(asMap(await client.get('/teams/$id')));

  Future<Team> createTeam({required String name, String? location}) async =>
      Team.fromJson(asMap(await client.post('/teams', body: {
        'name': name,
        'location': ?location,
      })));

  Future<void> deleteTeam(String id) => client.delete('/teams/$id');

  /// Add an existing player by id, or create one on the fly by name.
  Future<Team> addTeamMember(
    String teamId, {
    String? playerId,
    String? name,
    bool isCaptain = false,
  }) async =>
      Team.fromJson(asMap(await client.post('/teams/$teamId/members', body: {
        'player_id': ?playerId,
        'name': ?name,
        'is_captain': isCaptain,
      })));

  Future<Team> removeTeamMember(String teamId, String playerId) async =>
      Team.fromJson(asMap(await client.delete('/teams/$teamId/members/$playerId')));

  Future<TeamStats> teamStats(String id) async =>
      TeamStats.fromJson(asMap(await client.get('/teams/$id/stats')));

  Future<void> uploadTeamPhoto(String id, String path) =>
      client.upload('/teams/$id/photo', filePath: path);

  Future<void> deleteTeamPhoto(String id) => client.delete('/teams/$id/photo');

  // ========================================================== leaderboards

  Future<Leaderboards> leaderboards({
    String window = 'all',
    String? location,
    int? minInnings,
    int? limit,
  }) async {
    final q = <String, dynamic>{};
    if (window != 'all') q['window'] = window;
    if (location != null && location.isNotEmpty) q['location'] = location;
    if (minInnings != null) q['min_innings'] = minInnings;
    if (limit != null) q['limit'] = limit;
    return Leaderboards.fromJson(
      asMap(await client.get('/leaderboards', query: q.isEmpty ? null : q)),
    );
  }

  // =========================================================== tournaments

  Future<List<TournamentSummary>> tournaments() async =>
      asMapList(await client.get('/tournaments'))
          .map(TournamentSummary.fromJson)
          .toList();

  Future<Tournament> tournament(String id) async =>
      Tournament.fromJson(asMap(await client.get('/tournaments/$id')));

  Future<Tournament> createTournament({
    required String name,
    required String format,
    required List<String> teamIds,
    String formatId = 't20',
    MatchRules? rules,
    int numGroups = 2,
    int advancePerGroup = 2,
    int winPoints = 2,
    int tiePoints = 1,
    int nrPoints = 1,
    bool dlsEnabled = false,
  }) async =>
      Tournament.fromJson(asMap(await client.post('/tournaments', body: {
        'name': name,
        'format': format,
        'team_ids': teamIds,
        'format_id': formatId,
        if (rules != null) 'rules': rules.toJson(),
        if (format == TournamentFormats.groups) ...{
          'num_groups': numGroups,
          'advance_per_group': advancePerGroup,
        },
        if (format != TournamentFormats.knockout) ...{
          'win_points': winPoints,
          'tie_points': tiePoints,
          'nr_points': nrPoints,
        },
        'dls_enabled': dlsEnabled,
      })));

  Future<Tournament> updateTournamentSettings(String id, bool dlsEnabled) async =>
      Tournament.fromJson(asMap(await client.patch(
        '/tournaments/$id/settings',
        body: {'dls_enabled': dlsEnabled},
      )));

  Future<void> deleteTournament(String id) => client.delete('/tournaments/$id');

  Future<Fixture> startFixture(
    String fixtureId, {
    required List<String> squadAIds,
    required List<String> squadBIds,
    String batFirst = 'a',
  }) async =>
      Fixture.fromJson(asMap(await client.post(
        '/tournaments/fixtures/$fixtureId/start',
        body: {
          'squad_a_ids': squadAIds,
          'squad_b_ids': squadBIds,
          'bat_first': batFirst,
        },
      )));

  Future<List<TeamSquad>> tournamentSquads(String id) async =>
      asMapList(await client.get('/tournaments/$id/squads'))
          .map(TeamSquad.fromJson)
          .toList();

  Future<List<TeamSquad>> registerSquadPlayer(
    String tournamentId,
    String teamId,
    String playerId,
  ) async =>
      asMapList(await client.post(
        '/tournaments/$tournamentId/teams/$teamId/squad',
        body: {'player_id': playerId},
      )).map(TeamSquad.fromJson).toList();

  Future<List<TeamSquad>> unregisterSquadPlayer(
    String tournamentId,
    String teamId,
    String playerId,
  ) async =>
      asMapList(await client.delete(
        '/tournaments/$tournamentId/teams/$teamId/squad/$playerId',
      )).map(TeamSquad.fromJson).toList();

  // =============================================================== matches

  Future<List<MatchSummary>> matches() async =>
      asMapList(await client.get('/matches')).map(MatchSummary.fromJson).toList();

  Future<MatchState> match(String id) async =>
      MatchState.fromJson(asMap(await client.get('/matches/$id')));

  Future<MatchState> createMatch({
    required String teamA,
    required String teamB,
    String formatId = 't20',
    String batFirst = 'a',
    List<String>? squadA,
    List<String>? squadB,
    MatchRules? rules,
    List<String>? squadAIds,
    List<String>? squadBIds,
    String? teamAId,
    String? teamBId,
    String? venue,
    String? tournament,
    String? matchNo,
    String? tossWinner,
    String? tossDecision,
  }) async =>
      MatchState.fromJson(asMap(await client.post('/matches', body: {
        'team_a': teamA,
        'team_b': teamB,
        'format_id': formatId,
        'bat_first': batFirst,
        'squad_a': ?squadA,
        'squad_b': ?squadB,
        if (rules != null) 'rules': rules.toJson(),
        'squad_a_ids': ?squadAIds,
        'squad_b_ids': ?squadBIds,
        'team_a_id': ?teamAId,
        'team_b_id': ?teamBId,
        'venue': ?venue,
        'tournament': ?tournament,
        'match_no': ?matchNo,
        'toss_winner': ?tossWinner,
        'toss_decision': ?tossDecision,
      })));

  Future<void> deleteMatch(String id) => client.delete('/matches/$id');

  // ---- scoring

  Future<MatchState> setBowler(String id, String bowler) async =>
      MatchState.fromJson(
        asMap(await client.post('/matches/$id/bowler', body: {'bowler': bowler})),
      );

  Future<MatchState> recordBall(String id, BallRequest ball) async =>
      MatchState.fromJson(
        asMap(await client.post('/matches/$id/balls', body: ball.toJson())),
      );

  /// Correct an already-recorded delivery. `index` is its position within its
  /// own innings, as reported by the ball feed.
  Future<MatchState> editBall(String id, int index, BallRequest ball) async =>
      MatchState.fromJson(
        asMap(await client.put('/matches/$id/balls/$index', body: ball.toJson())),
      );

  Future<MatchState> deleteBall(String id, int index) async =>
      MatchState.fromJson(asMap(await client.delete('/matches/$id/balls/$index')));

  Future<MatchState> undo(String id) async =>
      MatchState.fromJson(asMap(await client.post('/matches/$id/undo')));

  Future<MatchState> startSecondInnings(String id) async =>
      MatchState.fromJson(asMap(await client.post('/matches/$id/second-innings')));

  Future<MatchState> declareInnings(String id) async =>
      MatchState.fromJson(asMap(await client.post('/matches/$id/declare')));

  Future<MatchState> startSuperOver(String id, {String? batFirst}) async =>
      MatchState.fromJson(asMap(await client.post(
        '/matches/$id/super-over',
        body: {'bat_first': batFirst},
      )));

  Future<MatchState> setRevisedTarget(String id, int target, {int? overs}) async =>
      MatchState.fromJson(asMap(await client.post(
        '/matches/$id/revised-target',
        body: {'target': target, 'overs': overs},
      )));

  Future<DlsSuggestion> suggestDls(String id, int team2Overs, {int? g50}) async =>
      DlsSuggestion.fromJson(asMap(await client.post(
        '/matches/$id/dls-suggest',
        body: {'team2_overs': team2Overs, 'g50': ?g50},
      )));

  Future<MatchState> interruptMatch(String id, String reason, {String? at}) async =>
      MatchState.fromJson(asMap(await client.post(
        '/matches/$id/interrupt',
        body: {'reason': reason, 'at': at},
      )));

  Future<MatchState> resumeMatch(String id, int overs, {String? at}) async =>
      MatchState.fromJson(asMap(await client.post(
        '/matches/$id/resume',
        body: {'overs': overs, 'at': at},
      )));

  Future<MatchState> cancelInterruption(String id) async =>
      MatchState.fromJson(asMap(await client.post('/matches/$id/interrupt/cancel')));

  Future<MatchState> abandonMatch(String id, String reason) async =>
      MatchState.fromJson(
        asMap(await client.post('/matches/$id/abandon', body: {'reason': reason})),
      );

  // ---- feeds and media

  Future<List<BallFeedItem>> ballFeed(String id) async =>
      asMapList(await client.get('/matches/$id/ball-feed'))
          .map(BallFeedItem.fromJson)
          .toList();

  Future<List<HighlightMoment>> matchHighlights(String id) async =>
      asMapList(await client.get('/matches/$id/highlights'))
          .map(HighlightMoment.fromJson)
          .toList();

  Future<List<CommentaryNote>> commentary(String id) async =>
      asMapList(await client.get('/matches/$id/commentary'))
          .map(CommentaryNote.fromJson)
          .toList();

  Future<CommentaryNote> postCommentary(String id, String text) async =>
      CommentaryNote.fromJson(asMap(
        await client.post('/matches/$id/commentary', body: {'text': text}),
      ));

  /// Records that you are commentating on this match (adds to your records).
  Future<void> markCommentating(String id) =>
      client.post('/matches/$id/commentate');

  Future<MatchState> setStreamUrl(String id, String? url) async =>
      MatchState.fromJson(asMap(await client.put(
        '/matches/$id/stream',
        body: {'stream_url': url},
      )));

  Future<List<MatchClip>> matchClips(String id) async =>
      asMapList(await client.get('/matches/$id/clips'))
          .map(MatchClip.fromJson)
          .toList();

  Future<List<MatchClip>> addClip(String id, String url, {String? label}) async =>
      asMapList(await client.post(
        '/matches/$id/clips',
        body: {'url': url, 'label': label},
      )).map(MatchClip.fromJson).toList();

  Future<List<MatchClip>> removeClip(String id, String clipId) async =>
      asMapList(await client.delete('/matches/$id/clips/$clipId'))
          .map(MatchClip.fromJson)
          .toList();

  Future<({bool ffmpegAvailable, bool hasRecording})> recordingStatus(
      String id) async {
    final r = asMap(await client.get('/matches/$id/recording'));
    return (
      ffmpegAvailable: asBool(r['ffmpeg_available']),
      hasRecording: asBool(r['has_recording']),
    );
  }

  Future<double> uploadRecording(
    String id,
    String path, {
    void Function(int, int)? onProgress,
  }) async {
    final r = asMap(await client.upload(
      '/matches/$id/recording',
      filePath: path,
      onProgress: onProgress,
    ));
    return asDouble(r['duration']);
  }

  Future<List<MatchClip>> generateAutoClips(String id, double anchor) async =>
      asMapList(await client.post(
        '/matches/$id/clips/auto',
        body: {'anchor': anchor},
      )).map(MatchClip.fromJson).toList();

  /// Every match's clips, grouped — the public highlights gallery.
  Future<List<MatchHighlightGroup>> allHighlights() async =>
      asMapList(await client.get('/highlights'))
          .map(MatchHighlightGroup.fromJson)
          .toList();

  /// Matches you are allowed to attach clips to.
  Future<List<MatchSummary>> myClipMatches() async =>
      asMapList(await client.get('/highlights/my-matches'))
          .map(MatchSummary.fromJson)
          .toList();

  // ---- fielding

  Future<List<FieldingEvent>> fieldingEvents(String id) async =>
      asMapList(await client.get('/matches/$id/fielding'))
          .map(FieldingEvent.fromJson)
          .toList();

  Future<FieldingEvent> addFieldingEvent(
    String id, {
    required String fielder,
    required String kind,
    int runs = 0,
    int innings = 1,
    String? bowler,
    String? batter,
    String? note,
    String? overBall,
  }) async =>
      FieldingEvent.fromJson(asMap(await client.post(
        '/matches/$id/fielding',
        body: {
          'fielder': fielder,
          'kind': kind,
          'runs': runs,
          'innings': innings,
          'bowler': ?bowler,
          'batter': ?batter,
          'note': ?note,
          'over_ball': ?overBall,
        },
      )));

  Future<void> deleteFieldingEvent(String id, String eventId) =>
      client.delete('/matches/$id/fielding/$eventId');

  // ---- officials

  Future<MatchOfficials> matchOfficials(String id) async =>
      MatchOfficials.fromJson(asMap(await client.get('/matches/$id/officials')));

  Future<List<PendingOfficialRequest>> pendingOfficialRequests() async =>
      asMapList(await client.get('/matches/officials/pending'))
          .map(PendingOfficialRequest.fromJson)
          .toList();

  Future<void> requestToOfficiate(String id) =>
      client.post('/matches/$id/officials/request');

  Future<void> approveOfficial(String id, String umpireId) =>
      client.post('/matches/$id/officials/$umpireId/approve');

  Future<void> removeOfficial(String id, String umpireId) =>
      client.delete('/matches/$id/officials/$umpireId');

  /// Live score frames. Each frame is a change notification, not full state —
  /// re-fetch the match when one arrives.
  Stream<SseEvent> matchStream(String id, {CancelToken? cancelToken}) =>
      client.sse('/matches/$id/stream', cancelToken: cancelToken);

  // ================================================================ social

  Future<FollowState> follow(String userId) async =>
      FollowState.fromJson(asMap(await client.post('/social/follow/$userId')));

  Future<FollowState> unfollow(String userId) async =>
      FollowState.fromJson(asMap(await client.delete('/social/follow/$userId')));

  Future<List<String>> following() async {
    final r = await client.get('/social/following');
    return r is List ? r.map((e) => '$e').toList() : <String>[];
  }

  Future<EntityFollowState> entityFollowState(String type, String id) async =>
      EntityFollowState.fromJson(
        asMap(await client.get('/social/follow/entity/$type/$id')),
      );

  Future<EntityFollowState> followEntity(String type, String id) async =>
      EntityFollowState.fromJson(
        asMap(await client.post('/social/follow/entity/$type/$id')),
      );

  Future<EntityFollowState> unfollowEntity(String type, String id) async =>
      EntityFollowState.fromJson(
        asMap(await client.delete('/social/follow/entity/$type/$id')),
      );

  Future<List<ActivityItem>> feed() async =>
      asMapList(await client.get('/social/feed'))
          .map(ActivityItem.fromJson)
          .toList();

  Future<List<AppNotification>> notifications() async =>
      asMapList(await client.get('/social/notifications'))
          .map(AppNotification.fromJson)
          .toList();

  Future<int> unreadNotificationCount() async =>
      asInt(asMap(await client.get('/social/notifications/unread'))['count']);

  Future<void> markNotificationsRead() =>
      client.post('/social/notifications/read');

  Future<void> markNotificationClicked(String id) =>
      client.post('/social/notifications/$id/click');

  Future<void> deleteNotification(String id) =>
      client.delete('/social/notifications/$id');

  Future<NotificationPrefs> notificationPrefs() async =>
      NotificationPrefs.fromJson(
        asMap(await client.get('/social/notifications/preferences')),
      );

  Future<NotificationPrefs> saveNotificationPrefs(NotificationPrefs p) async =>
      NotificationPrefs.fromJson(asMap(await client.put(
        '/social/notifications/preferences',
        body: p.toJson(),
      )));

  Stream<SseEvent> notificationStream(String token, {CancelToken? cancelToken}) =>
      client.sse(
        '/social/notifications/stream',
        query: {'token': token},
        cancelToken: cancelToken,
      );

  // ============================================================== messages

  Future<List<Conversation>> conversations() async =>
      asMapList(await client.get('/messages')).map(Conversation.fromJson).toList();

  Future<MessageThread> thread(String userId) async =>
      MessageThread.fromJson(asMap(await client.get('/messages/$userId')));

  Future<DirectMessage> sendMessage(String recipientId, String text) async =>
      DirectMessage.fromJson(asMap(await client.post(
        '/messages',
        body: {'recipient_id': recipientId, 'text': text},
      )));

  Future<int> unreadMessageCount() async =>
      asInt(asMap(await client.get('/messages/unread'))['count']);

  // =========================================================== looking-for

  Future<List<LookingForPost>> lookingFor({String? kind, String? location}) async {
    final q = <String, dynamic>{};
    if (kind != null && kind.isNotEmpty) q['kind'] = kind;
    if (location != null && location.isNotEmpty) q['location'] = location;
    return asMapList(await client.get('/looking-for', query: q.isEmpty ? null : q))
        .map(LookingForPost.fromJson)
        .toList();
  }

  Future<List<LookingForPost>> myLookingFor() async =>
      asMapList(await client.get('/looking-for/mine'))
          .map(LookingForPost.fromJson)
          .toList();

  Future<LookingForPost> postLookingFor({
    required String kind,
    required String text,
    String? location,
    String? role,
  }) async =>
      LookingForPost.fromJson(asMap(await client.post('/looking-for', body: {
        'kind': kind,
        'text': text,
        'location': ?location,
        'role': ?role,
      })));

  Future<void> closeLookingFor(String id) =>
      client.post('/looking-for/$id/close');

  Future<void> deleteLookingFor(String id) => client.delete('/looking-for/$id');

  // ================================================================ venues

  Future<List<Venue>> venues({String? kind, String? location, String? q}) async {
    final query = <String, dynamic>{};
    if (kind != null && kind.isNotEmpty) query['kind'] = kind;
    if (location != null && location.isNotEmpty) query['location'] = location;
    if (q != null && q.isNotEmpty) query['q'] = q;
    return asMapList(
      await client.get('/venues', query: query.isEmpty ? null : query),
    ).map(Venue.fromJson).toList();
  }

  Future<Venue> venue(String id) async =>
      Venue.fromJson(asMap(await client.get('/venues/$id')));

  Future<Venue> createVenue({
    required String name,
    String kind = 'ground',
    String? city,
    String? address,
    String? contact,
    String? note,
  }) async =>
      Venue.fromJson(asMap(await client.post('/venues', body: {
        'name': name,
        'kind': kind,
        'city': ?city,
        'address': ?address,
        'contact': ?contact,
        'note': ?note,
      })));

  Future<void> deleteVenue(String id) => client.delete('/venues/$id');

  // ================================================================= admin

  Future<List<RoleRequest>> roleRequests() async =>
      asMapList(await client.get('/admin/role-requests'))
          .map(RoleRequest.fromJson)
          .toList();

  Future<void> approveRole(String userId) =>
      client.post('/admin/role-requests/$userId/approve');

  Future<void> rejectRole(String userId) =>
      client.post('/admin/role-requests/$userId/reject');

  Future<({int recipients, int audience})> sendAnnouncement({
    required String title,
    required String text,
    String category = 'system',
    String link = '',
  }) async {
    final r = asMap(await client.post('/admin/announcements', body: {
      'title': title,
      'text': text,
      'category': category,
      'link': link,
    }));
    return (recipients: asInt(r['recipients']), audience: asInt(r['audience']));
  }

  Future<List<AnnouncementCampaign>> announcementAnalytics() async =>
      asMapList(await client.get('/admin/announcements/analytics'))
          .map(AnnouncementCampaign.fromJson)
          .toList();
}

/// A saved custom rulebook.
class RuleTemplate {
  final String id;
  final String name;
  final MatchRules rules;

  const RuleTemplate({
    required this.id,
    required this.name,
    required this.rules,
  });

  factory RuleTemplate.fromJson(Map<String, dynamic> j) => RuleTemplate(
        id: asStr(j['id']),
        name: asStr(j['name']),
        rules: MatchRules.fromJson(asMap(j['rules'])),
      );

  /// "8-a-side · 6ov · rule-out · 1 PP"
  String get summary {
    final r = rules;
    final bits = <String>[
      '${r.playersPerSide}-a-side',
      '${r.oversPerInnings}ov',
      r.overBoundaryOut ? 'rule-out' : 'full ground',
      if (r.powerplays.isNotEmpty) '${r.powerplays.length} PP',
      if (r.superOverOnTie) 'super over',
      if (r.dlsEnabled) 'DLS',
    ];
    return bits.join(' · ');
  }
}
