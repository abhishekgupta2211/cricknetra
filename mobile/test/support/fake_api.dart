import 'package:cricnetra/core/api/api_client.dart';
import 'package:cricnetra/core/api/api_service.dart';
import 'package:cricnetra/core/auth/auth_provider.dart';
import 'package:cricnetra/core/models/career.dart';
import 'package:cricnetra/core/models/match.dart';
import 'package:cricnetra/core/models/roster.dart';
import 'package:cricnetra/core/models/rules.dart';
import 'package:cricnetra/core/models/social.dart';
import 'package:cricnetra/core/models/tournament.dart';
import 'package:cricnetra/core/models/user.dart';
import 'package:cricnetra/core/storage/token_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// An ApiService that answers from fixtures instead of the network.
///
/// The fixtures are the real shapes captured from a running server, so a screen
/// that renders here renders against the real thing.
class FakeApi implements ApiService {
  @override
  final ApiClient client;

  FakeApi() : client = ApiClient(tokenStorage: TokenStorage());

  /// Set to make the next call fail, for error-state tests.
  Object? failWith;

  /// Replaces the career fixture, for testing an empty or unusual career.
  PlayerHistory? historyOverride;

  Future<T> _answer<T>(T value) async {
    if (failWith != null) throw failWith!;
    return value;
  }

  // ---------------------------------------------------------------- fixtures

  static final adminUser = AppUser.fromJson({
    'id': '1',
    'full_name': 'Seed Admin',
    'username': 'demoadmin',
    'mobile_no': '9999999999',
    'user_code': 'CN000001',
    'role_code': 'ADM001',
    'role': 'admin',
    'is_active': true,
    'is_verified': true,
    'capabilities': [
      'match.commentate',
      'match.create',
      'match.score',
      'rules.manage',
      'team.create',
      'tournament.create',
    ],
    'records': {
      'matches_scored': 2,
      'matches_umpired': 0,
      'matches_commentated': 1,
      'tournaments_organized': 1,
      'teams_owned': 2,
    },
  });

  /// A live T20 innings mid-over, the state a scorer actually looks at.
  static final liveMatch = MatchState.fromJson({
    'id': '1',
    'team_a': 'Mumbai Strikers',
    'team_b': 'Chennai Kings',
    'bat_first': 'Mumbai Strikers',
    'format_id': 't20',
    'rules_name': 'T20',
    'rules': const MatchRules(
      name: 'T20',
      formatId: 't20',
      oversPerInnings: 20,
      maxOversPerBowler: 4,
      powerplays: [PowerplayRange(startOver: 1, endOver: 6)],
    ).toJson(),
    'current_innings': 1,
    'awaiting_bowler': false,
    'over_pending': false,
    'available_bowlers': ['Deepak Chahar', 'Avesh Khan', 'Prasidh Krishna'],
    'can_start_second_innings': false,
    'innings': [
      {
        'batting_team': 'Mumbai Strikers',
        'bowling_team': 'Chennai Kings',
        'runs': 24,
        'wickets': 1,
        'legal_balls': 12,
        'overs_str': '2.0',
        'max_overs': 20,
        'max_wickets': 10,
        'extras': {'wides': 1, 'leg_byes': 1, 'total': 2},
        'run_rate': 12.0,
        'this_over': ['1', '4', 'W', '•', '3', '1'],
        'manhattan': [13, 11],
        'worm': [13, 24],
        'wagon': [
          {'x': 0.62, 'y': 0.48, 'runs': 4, 'batter': 'Rohit Sharma', 'over': '0.0'},
          {'x': -0.35, 'y': 0.85, 'runs': 6, 'batter': 'Virat Kohli', 'over': '0.2'},
        ],
        'batters': [
          {
            'name': 'Rohit Sharma',
            'order': 1,
            'runs': 11,
            'balls': 7,
            'fours': 2,
            'out': true,
            'how_out': 'bowled',
            'dismissal_text': 'b Arshdeep Singh',
            'has_batted': true,
            'strike_rate': 157.1,
            'player_id': '1',
          },
          {
            'name': 'Virat Kohli',
            'order': 2,
            'runs': 8,
            'balls': 4,
            'sixes': 1,
            'on_strike': true,
            'has_batted': true,
            'strike_rate': 200.0,
            'player_id': '2',
          },
          {
            'name': 'KL Rahul',
            'order': 3,
            'runs': 3,
            'balls': 2,
            'has_batted': true,
            'strike_rate': 150.0,
            'player_id': '4',
          },
        ],
        'bowlers': [
          {
            'name': 'Deepak Chahar',
            'order': 1,
            'overs': '1.0',
            'runs': 13,
            'economy': 13.0,
            'wides': 1,
          },
          {
            'name': 'Arshdeep Singh',
            'order': 2,
            'overs': '1.0',
            'runs': 9,
            'wickets': 1,
            'economy': 9.0,
          },
        ],
        'fall_of_wickets': [
          {'wicket': 1, 'score': 20, 'batter_out': 'Rohit Sharma', 'over': '1.3'},
        ],
        'partnerships': [
          {
            'wicket': 1,
            'runs': 20,
            'balls': 9,
            'batter_a': 'Rohit Sharma',
            'batter_b': 'Virat Kohli',
          },
          {
            'wicket': 2,
            'runs': 4,
            'balls': 3,
            'batter_a': 'Virat Kohli',
            'batter_b': 'KL Rahul',
            'unbroken': true,
          },
        ],
        'striker': 'Virat Kohli',
        'non_striker': 'KL Rahul',
        'bowler': 'Arshdeep Singh',
        'current_over': 3,
        'in_powerplay': true,
        'powerplay_label': 'Powerplay',
        'fielders_outside_limit': 2,
      }
    ],
    'meta': {
      'venue': 'Wankhede Ground',
      'tournament': 'City Premier League',
      'match_no': '1',
      'toss_text': 'Mumbai Strikers won the toss and chose to bat',
    },
  });

  /// The same match, but between overs, so the bowler picker is showing.
  static MatchState get awaitingBowler => MatchState.fromJson({
        ...liveMatch.toJsonForTest(),
        'awaiting_bowler': true,
        'over_pending': true,
      });

  static final playerFixtures = [
    Player.fromJson({'id': '1', 'name': 'Rohit Sharma', 'code': 'P00001'}),
    Player.fromJson({'id': '2', 'name': 'Virat Kohli', 'code': 'P00002'}),
    Player.fromJson({'id': '3', 'name': 'Jasprit Bumrah', 'code': 'P00003'}),
  ];

  static final teamFixtures = [
    Team.fromJson({
      'id': '1',
      'name': 'Mumbai Strikers',
      'location': 'Mumbai',
      'members': [
        {'player_id': '1', 'name': 'Rohit Sharma', 'code': 'P00001'},
        {'player_id': '2', 'name': 'Virat Kohli', 'code': 'P00002'},
      ],
    }),
    Team.fromJson({'id': '2', 'name': 'Chennai Kings', 'location': 'Chennai'}),
  ];

  static final tournamentFixture = Tournament.fromJson({
    'id': '1',
    'name': 'City Premier League',
    'format': 'round_robin',
    'status': 'active',
    'teams': [
      {'id': '1', 'name': 'Mumbai Strikers'},
      {'id': '2', 'name': 'Chennai Kings'},
    ],
    'fixtures': [
      {
        'id': '1',
        'round': 1,
        'position': 1,
        'team_a': {'id': '1', 'name': 'Mumbai Strikers'},
        'team_b': {'id': '2', 'name': 'Chennai Kings'},
        'status': 'scheduled',
      }
    ],
    'standings': [
      {'team_id': '1', 'name': 'Mumbai Strikers', 'played': 1, 'won': 1, 'points': 2, 'nrr': 1.25},
      {'team_id': '2', 'name': 'Chennai Kings', 'played': 1, 'lost': 1, 'nrr': -1.25},
    ],
    'config': {'win_points': 2, 'tie_points': 1, 'nr_points': 1},
  });

  /// A two-season career across two competitions, with a live game in it —
  /// the shape that exercises every branch of the career screen.
  static final historyFixture = PlayerHistory.fromJson({
    'player': {'id': '1', 'name': 'Rohit Sharma', 'code': 'P00001'},
    'debut': '2025-04-02T10:00:00',
    'last_played': '2026-09-05T15:00:00',
    'matches_played': 3,
    'won': 1,
    'lost': 1,
    'tied': 0,
    'no_result': 0,
    'win_pct': 50.0,
    'batting': {
      'matches': 3, 'innings': 3, 'runs': 96, 'balls': 60, 'highest': 62,
      'average': 48.0, 'strike_rate': 160.0, 'fours': 9, 'sixes': 4,
      'fifties': 1, 'hundreds': 0, 'not_outs': 1,
    },
    'bowling': {
      'matches': 2, 'innings': 2, 'balls': 24, 'overs': '4.0', 'runs': 30,
      'wickets': 3, 'average': 10.0, 'economy': 7.5, 'best': '2/12',
      'maidens': 0,
    },
    'fielding': {'catches': 2, 'run_outs': 1, 'stumpings': 0, 'runs_saved': 4},
    'matches': [
      {
        'match_id': '3',
        'played_on': '2026-09-05T15:00:00',
        'format': 'T20',
        'team': 'Mumbai Strikers',
        'opponent': 'Chennai Kings',
        'tournament': 'City Premier League',
        'venue': 'Wankhede Ground',
        'outcome': 'in_progress',
        'batted': true, 'runs': 8, 'balls': 5, 'bat_line': '8 (5)',
      },
      {
        'match_id': '2',
        'played_on': '2026-03-11T15:00:00',
        'format': 'T20',
        'team': 'Mumbai Strikers',
        'opponent': 'Chennai Kings',
        'tournament': 'Winter Shield',
        'venue': 'Shivaji Park Academy',
        'result': 'Mumbai Strikers won by 26 run(s)',
        'outcome': 'won',
        'batted': true, 'runs': 62, 'balls': 38, 'fours': 6, 'sixes': 3,
        'not_out': true, 'bat_line': '62* (38)',
        'bowled': true, 'overs': '2.0', 'wickets': 2, 'runs_conceded': 12,
        'economy': 6.0, 'bowl_line': '2/12 (2.0)',
        'catches': 1,
      },
      {
        'match_id': '1',
        'played_on': '2025-04-02T10:00:00',
        'format': 'Box',
        'team': 'Mumbai Strikers',
        'opponent': 'Delhi Riders',
        'result': 'Delhi Riders won by 4 wicket(s)',
        'outcome': 'lost',
        'batted': true, 'runs': 26, 'balls': 17, 'fours': 3, 'sixes': 1,
        'how_out': 'bowled', 'dismissal_text': 'b Bumrah', 'bat_line': '26 (17)',
        'bowled': true, 'overs': '2.0', 'wickets': 1, 'runs_conceded': 18,
        'bowl_line': '1/18 (2.0)',
        'catches': 1, 'run_outs': 1,
      },
    ],
    'by_tournament': [
      {
        'key': 'Winter Shield', 'label': 'Winter Shield',
        'matches': 1, 'won': 1, 'lost': 0,
        'batting': {'innings': 1, 'runs': 62, 'highest': 62, 'strike_rate': 163.2, 'not_outs': 1},
        'bowling': {'innings': 1, 'balls': 12, 'overs': '2.0', 'wickets': 2, 'runs': 12, 'economy': 6.0, 'best': '2/12'},
        'fielding': {'catches': 1},
      },
      {
        'key': 'City Premier League', 'label': 'City Premier League',
        'matches': 1, 'won': 0, 'lost': 0,
        'batting': {'innings': 1, 'runs': 8, 'highest': 8, 'strike_rate': 160.0},
        'bowling': {},
        'fielding': {},
      },
    ],
    'by_year': [
      {
        'key': '2026', 'label': '2026', 'matches': 2, 'won': 1, 'lost': 0,
        'batting': {'innings': 2, 'runs': 70, 'highest': 62},
        'bowling': {'balls': 12, 'overs': '2.0', 'wickets': 2},
        'fielding': {'catches': 1},
      },
      {
        'key': '2025', 'label': '2025', 'matches': 1, 'won': 0, 'lost': 1,
        'batting': {'innings': 1, 'runs': 26, 'highest': 26},
        'bowling': {'balls': 12, 'overs': '2.0', 'wickets': 1},
        'fielding': {'catches': 1, 'run_outs': 1},
      },
    ],
    'by_team': [
      {
        'key': 'Mumbai Strikers', 'label': 'Mumbai Strikers',
        'matches': 3, 'won': 1, 'lost': 1,
        'batting': {'innings': 3, 'runs': 96, 'highest': 62},
        'bowling': {'balls': 24, 'overs': '4.0', 'wickets': 3},
        'fielding': {'catches': 2, 'run_outs': 1},
      },
    ],
  });

  // ------------------------------------------------------------ the surface

  @override
  Future<MatchState> match(String id) => _answer(liveMatch);

  @override
  Future<List<MatchSummary>> matches() => _answer([
        MatchSummary.fromJson({
          'id': '1',
          'team_a': 'Mumbai Strikers',
          'team_b': 'Chennai Kings',
          'status': 'in_progress',
        })
      ]);

  @override
  Future<MatchOfficials> matchOfficials(String id) => _answer(
        MatchOfficials.fromJson({
          'can_score': true,
          'is_manager': true,
          'my_status': 'none',
          'officials': const [],
        }),
      );

  @override
  Future<List<BallFeedItem>> ballFeed(String id) => _answer([
        BallFeedItem.fromJson({
          'innings': 'Mumbai Strikers innings',
          'over_ball': '1.3',
          'kind': 'wicket',
          'bowler': 'Arshdeep Singh',
          'striker': 'Rohit Sharma',
          'text': 'Arshdeep Singh to Rohit Sharma, OUT!',
          'idx': 9,
          'editable': true,
        }),
        BallFeedItem.fromJson({
          'innings': 'Mumbai Strikers innings',
          'over_ball': '1.2',
          'kind': 'four',
          'runs': 4,
          'text': 'Arshdeep Singh to Rohit Sharma, FOUR!',
          'idx': 8,
          'editable': true,
        }),
      ]);

  @override
  Future<List<HighlightMoment>> matchHighlights(String id) => _answer([
        HighlightMoment.fromJson({
          'innings': 'Mumbai Strikers innings',
          'over_ball': '1.3',
          'kind': 'wicket',
          'title': 'WICKET',
          'text': 'Rohit Sharma b Arshdeep Singh',
        })
      ]);

  @override
  Future<List<CommentaryNote>> commentary(String id) => _answer([
        CommentaryNote.fromJson({
          'id': '1',
          'author_name': 'Seed Admin',
          'text': 'Cracking start from the openers.',
          'when': DateTime.now().toIso8601String(),
        })
      ]);

  @override
  Future<List<FieldingEvent>> fieldingEvents(String id) => _answer([
        FieldingEvent.fromJson({
          'id': '1',
          'match_id': '1',
          'innings': 1,
          'fielder': 'Rinku Singh',
          'kind': 'save',
          'runs': 2,
        })
      ]);

  @override
  Future<List<Player>> players() => _answer(playerFixtures);

  @override
  Future<List<Team>> teams() => _answer(teamFixtures);

  @override
  Future<Team> team(String id) =>
      _answer(teamFixtures.firstWhere((t) => t.id == id));

  @override
  Future<TeamStats> teamStats(String id) => _answer(TeamStats.fromJson({
        'team_id': id,
        'name': 'Mumbai Strikers',
        'played': 2,
        'won': 1,
        'lost': 1,
        'win_pct': 50.0,
        'runs_for': 240,
        'runs_against': 210,
      }));

  @override
  Future<Tournament> tournament(String id) => _answer(tournamentFixture);

  @override
  Future<List<TournamentSummary>> tournaments() => _answer([
        TournamentSummary.fromJson({
          'id': '1',
          'name': 'City Premier League',
          'format': 'round_robin',
          'teams': [
            {'id': '1', 'name': 'Mumbai Strikers'},
            {'id': '2', 'name': 'Chennai Kings'},
          ],
        })
      ]);

  @override
  Future<List<TeamSquad>> tournamentSquads(String id) => _answer([
        TeamSquad.fromJson({
          'team_id': '1',
          'team_name': 'Mumbai Strikers',
          'players': [
            {'id': '1', 'name': 'Rohit Sharma', 'code': 'P00001'},
          ],
        })
      ]);

  @override
  Future<List<PresetSummary>> presets() => _answer([
        PresetSummary.fromJson({
          'id': 't20',
          'name': 'T20',
          'overs_per_innings': 20,
          'players_per_side': 11,
        })
      ]);

  @override
  Future<MatchRules> preset(String formatId) =>
      _answer(const MatchRules(name: 'T20', formatId: 't20'));

  @override
  Future<List<RuleTemplate>> ruleTemplates() => _answer([
        RuleTemplate(
          id: '1',
          name: 'Society box',
          rules: const MatchRules(
            name: 'Society box',
            playersPerSide: 8,
            oversPerInnings: 6,
            overBoundaryOut: true,
          ),
        )
      ]);

  @override
  Future<RuleTemplate> ruleTemplate(String id) async =>
      (await ruleTemplates()).first;

  @override
  Future<Leaderboards> leaderboards({
    String window = 'all',
    String? location,
    int? minInnings,
    int? limit,
  }) =>
      _answer(Leaderboards.fromJson({
        'min_innings': 1,
        'window': window,
        'most_runs': [
          {'player_id': '1', 'name': 'Rohit Sharma', 'value': 11.0, 'detail': '1 inns'},
        ],
        'mvp': [
          {'player_id': '2', 'name': 'Virat Kohli', 'value': 28.0},
        ],
      }));

  @override
  Future<AppUser> me() => _answer(adminUser);

  @override
  Future<List<AppNotification>> notifications() => _answer([
        AppNotification.fromJson({
          'id': '1',
          'kind': 'match',
          'category': 'match',
          'title': 'Wicket',
          'text': 'Rohit Sharma b Arshdeep Singh',
          'link': '#/match/1',
          'is_read': false,
          'when': DateTime.now().toIso8601String(),
        })
      ]);

  @override
  Future<int> unreadNotificationCount() => _answer(1);

  @override
  Future<int> unreadMessageCount() => _answer(0);

  @override
  Future<NotificationPrefs> notificationPrefs() =>
      _answer(const NotificationPrefs());

  @override
  Future<NotificationPrefs> saveNotificationPrefs(NotificationPrefs p) =>
      _answer(p);

  @override
  Future<List<ActivityItem>> feed() => _answer([
        ActivityItem.fromJson({
          'id': '1',
          'actor_id': '1',
          'actor_name': 'demoadmin',
          'kind': 'match',
          'text': 'started scoring Mumbai Strikers vs Chennai Kings',
          'link': '#/match/1',
          'when': DateTime.now().toIso8601String(),
        })
      ]);

  @override
  Future<List<Conversation>> conversations() => _answer([
        Conversation.fromJson({
          'other_id': '2',
          'other_name': 'Rahul',
          'last_text': 'See you Sunday',
          'last_when': DateTime.now().toIso8601String(),
          'unread': 2,
        })
      ]);

  @override
  Future<MessageThread> thread(String userId) => _answer(MessageThread.fromJson({
        'other_id': userId,
        'other_name': 'Rahul',
        'messages': [
          {
            'id': '1',
            'sender_id': '2',
            'recipient_id': '1',
            'text': 'See you Sunday',
            'when': DateTime.now().toIso8601String(),
          }
        ],
      }));

  @override
  Future<List<LookingForPost>> lookingFor({String? kind, String? location}) =>
      _answer([
        LookingForPost.fromJson({
          'id': '1',
          'author_id': '1',
          'author_name': 'Seed Admin',
          'kind': 'player',
          'text': 'Need a fast bowler for Sunday league.',
          'location': 'Mumbai',
          'status': 'open',
          'mine': true,
          'when': DateTime.now().toIso8601String(),
        })
      ]);

  @override
  Future<List<Venue>> venues({String? kind, String? location, String? q}) =>
      _answer([
        Venue.fromJson({
          'id': '1',
          'name': 'Wankhede Ground',
          'kind': 'ground',
          'city': 'Mumbai',
          'contact': '9820011223',
        })
      ]);

  @override
  Future<List<PublicUser>> users({String? role}) => _answer([
        PublicUser.fromJson({
          'id': '2',
          'full_name': 'Rahul Yadav',
          'username': 'rahul',
          'role': role ?? 'player',
          'mobile_no': '9820011223',
          'is_verified': true,
        })
      ]);

  @override
  Future<List<String>> following() => _answer(const <String>[]);

  @override
  Future<List<RoleRequest>> roleRequests() => _answer([
        RoleRequest.fromJson({
          'user_id': '3',
          'full_name': 'New Umpire',
          'username': 'newump',
          'requested_role': 'umpire',
        })
      ]);

  @override
  Future<List<AnnouncementCampaign>> announcementAnalytics() =>
      _answer(const <AnnouncementCampaign>[]);

  @override
  Future<List<MatchHighlightGroup>> allHighlights() => _answer([
        MatchHighlightGroup.fromJson({
          'match_id': '1',
          'team_a': 'Mumbai Strikers',
          'team_b': 'Chennai Kings',
          'live': true,
          'status_label': 'Live',
          'fmt': 'T20',
          'clips': const [],
        })
      ]);

  @override
  Future<PlayerStats> playerStats(String id) => _answer(PlayerStats.fromJson({
        'player': {'id': id, 'name': 'Rohit Sharma', 'code': 'P00001'},
        'batting': {
          'matches': 2,
          'innings': 2,
          'runs': 11,
          'balls': 7,
          'highest': 11,
          'average': 11.0,
          'strike_rate': 157.1,
          'fours': 2,
        },
        'bowling': {'matches': 0},
        'fielding': {'catches': 1},
        'recent': [
          {'match_id': '1', 'teams': 'Mumbai v Chennai', 'bat': '11 (7)'},
        ],
      }));

  @override
  Future<PlayerInsights> playerInsights(String id) => _answer(
        PlayerInsights.fromJson({
          'player': {'id': id, 'name': 'Rohit Sharma'},
          'batting': {'balls_faced': 7, 'dot_balls': 2, 'dot_pct': 28.6, 'fours': 2},
          'bowling': {},
        }),
      );

  @override
  Future<PlayerSplits> playerSplits(String id) => _answer(
        PlayerSplits.fromJson({
          'player': {'id': id, 'name': 'Rohit Sharma'},
          'by_format': [],
          'by_ball': [],
        }),
      );

  @override
  Future<List<PlayerAward>> playerAwards(String id) =>
      _answer(const <PlayerAward>[]);

  @override
  Future<PlayerHistory> playerHistory(String id) =>
      _answer(historyOverride ?? historyFixture);

  @override
  Future<List<Player>> claimablePlayers() => _answer(const <Player>[]);

  @override
  Future<List<Player>> myPlayers() => _answer(const <Player>[]);

  @override
  Future<UserProfile?> myProfile() async => null;

  @override
  Future<List<PendingOfficialRequest>> pendingOfficialRequests() =>
      _answer(const <PendingOfficialRequest>[]);

  @override
  Future<SearchResults> search(String q) =>
      _answer(SearchResults.fromJson({'query': q}));

  /// Everything not needed by a rendering test throws loudly, so a screen that
  /// unexpectedly calls the network fails the test instead of hanging.
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('FakeApi: ${invocation.memberName} not stubbed');
}

/// Overrides that put the app in a signed-in state with fixture data.
List<Override> signedInOverrides(FakeApi api) => [
      apiProvider.overrideWithValue(api),
      authControllerProvider.overrideWith(
        (ref) => _StubAuth(api: api, user: FakeApi.adminUser),
      ),
    ];

/// Overrides for a guest, to check the gates.
List<Override> signedOutOverrides(FakeApi api) => [
      apiProvider.overrideWithValue(api),
      authControllerProvider.overrideWith((ref) => _StubAuth(api: api)),
    ];

class _StubAuth extends AuthController {
  _StubAuth({required FakeApi api, AppUser? user})
      : super(api: api, tokens: TokenStorage(), client: api.client) {
    state = user == null
        ? const AuthState(status: AuthStatus.signedOut)
        : AuthState(status: AuthStatus.signedIn, user: user);
  }

  // The real controller reads stored tokens on construction; a test should not.
  @override
  Future<void> restore() async {}
}

/// `MatchState` has no toJson (it is read-only from the server), so tests that
/// need a variant rebuild from the fixture map.
extension MatchStateTestJson on MatchState {
  Map<String, dynamic> toJsonForTest() => {
        'id': id,
        'team_a': teamA,
        'team_b': teamB,
        'bat_first': batFirst,
        'format_id': formatId,
        'rules_name': rulesName,
        'rules': rules.toJson(),
        'current_innings': currentInnings,
        'available_bowlers': availableBowlers,
        'can_start_second_innings': canStartSecondInnings,
        'innings': [
          for (final i in innings)
            {
              'batting_team': i.battingTeam,
              'bowling_team': i.bowlingTeam,
              'runs': i.runs,
              'wickets': i.wickets,
              'overs_str': i.oversStr,
              'max_overs': i.maxOvers,
              'max_wickets': i.maxWickets,
              'run_rate': i.runRate,
              'this_over': i.thisOver,
              'striker': i.striker,
              'non_striker': i.nonStriker,
              'bowler': i.bowler,
              'current_over': i.currentOver,
            }
        ],
      };
}
