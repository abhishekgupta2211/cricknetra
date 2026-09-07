/// Community: feed, notifications, messages, the Looking For board, venues,
/// search results and leaderboards.
library;

import 'json.dart';
import 'roster.dart';
import 'tournament.dart';
import 'user.dart';

class FollowState {
  final bool isFollowing;
  final int followers;
  final int following;

  const FollowState({
    this.isFollowing = false,
    this.followers = 0,
    this.following = 0,
  });

  factory FollowState.fromJson(Map<String, dynamic> j) => FollowState(
        isFollowing: asBool(j['is_following']),
        followers: asInt(j['followers']),
        following: asInt(j['following']),
      );
}

class EntityFollowState {
  final bool isFollowing;
  final int followers;

  const EntityFollowState({this.isFollowing = false, this.followers = 0});

  factory EntityFollowState.fromJson(Map<String, dynamic> j) =>
      EntityFollowState(
        isFollowing: asBool(j['is_following']),
        followers: asInt(j['followers']),
      );
}

/// Non-user things you can follow.
class FollowEntities {
  const FollowEntities._();
  static const team = 'team';
  static const player = 'player';
  static const tournament = 'tournament';
  static const match = 'match';
  static const club = 'club';
  static const academy = 'academy';
}

/// One line in the activity feed.
class ActivityItem {
  final String id;
  final String actorId;
  final String actorName;

  /// match | team | tournament
  final String kind;
  final String text;
  final String link;
  final String when;

  const ActivityItem({
    required this.id,
    this.actorId = '',
    this.actorName = '',
    this.kind = '',
    this.text = '',
    this.link = '',
    this.when = '',
  });

  factory ActivityItem.fromJson(Map<String, dynamic> j) => ActivityItem(
        id: asStr(j['id']),
        actorId: asStr(j['actor_id']),
        actorName: asStr(j['actor_name']),
        kind: asStr(j['kind']),
        text: asStr(j['text']),
        link: asStr(j['link']),
        when: asStr(j['when']),
      );
}

class AppNotification {
  final String id;
  final String kind;
  final String text;
  final String link;
  final bool isRead;
  final String when;
  final String category;
  final String title;

  /// How many events were folded into this one.
  final int count;

  const AppNotification({
    required this.id,
    this.kind = '',
    this.text = '',
    this.link = '',
    this.isRead = false,
    this.when = '',
    this.category = '',
    this.title = '',
    this.count = 1,
  });

  factory AppNotification.fromJson(Map<String, dynamic> j) => AppNotification(
        id: asStr(j['id']),
        kind: asStr(j['kind']),
        text: asStr(j['text']),
        link: asStr(j['link']),
        isRead: asBool(j['is_read']),
        when: asStr(j['when']),
        category: asStr(j['category']),
        title: asStr(j['title']),
        count: asInt(j['count'], 1),
      );

  String get effectiveCategory => category.isEmpty ? 'social' : category;
}

/// Notification categories, matching the preference keys.
class NotificationCategories {
  const NotificationCategories._();
  static const order = <String>[
    'match',
    'tournament',
    'team',
    'player',
    'social',
    'achievement',
    'system',
    'admin',
    'marketing',
  ];

  static String label(String c) => switch (c) {
        'match' => 'Matches',
        'tournament' => 'Tournaments',
        'team' => 'Teams',
        'player' => 'Players',
        'social' => 'Social',
        'achievement' => 'Achievements',
        'system' => 'System',
        'admin' => 'Admin',
        'marketing' => 'Tips & offers',
        _ => 'Other',
      };

  static String emoji(String c) => switch (c) {
        'match' => '\u{1f3cf}',
        'tournament' => '\u{1f3c6}',
        'team' => '\u{1f6e1}',
        'player' => '\u{1f9e2}',
        'social' => '\u{1f465}',
        'achievement' => '\u{1f3c5}',
        'system' => '⚙',
        'admin' => '\u{1f6e0}',
        'marketing' => '\u{1f4e3}',
        _ => '\u{1f514}',
      };
}

/// Category toggles plus delivery channels.
class NotificationPrefs {
  final bool match;
  final bool tournament;
  final bool team;
  final bool player;
  final bool social;
  final bool system;
  final bool achievement;
  final bool marketing;
  final bool emailEnabled;
  final bool pushEnabled;
  final bool sound;

  /// Local hour the do-not-disturb window opens and closes (0-23), or null.
  final int? quietStart;
  final int? quietEnd;

  /// Minutes from UTC to local.
  final int tzOffset;

  const NotificationPrefs({
    this.match = true,
    this.tournament = true,
    this.team = true,
    this.player = true,
    this.social = true,
    this.system = true,
    this.achievement = true,
    this.marketing = false,
    this.emailEnabled = false,
    this.pushEnabled = true,
    this.sound = true,
    this.quietStart,
    this.quietEnd,
    this.tzOffset = 0,
  });

  factory NotificationPrefs.fromJson(Map<String, dynamic> j) =>
      NotificationPrefs(
        match: asBool(j['match'], true),
        tournament: asBool(j['tournament'], true),
        team: asBool(j['team'], true),
        player: asBool(j['player'], true),
        social: asBool(j['social'], true),
        system: asBool(j['system'], true),
        achievement: asBool(j['achievement'], true),
        marketing: asBool(j['marketing']),
        emailEnabled: asBool(j['email_enabled']),
        pushEnabled: asBool(j['push_enabled'], true),
        sound: asBool(j['sound'], true),
        quietStart: asIntOrNull(j['quiet_start']),
        quietEnd: asIntOrNull(j['quiet_end']),
        tzOffset: asInt(j['tz_offset']),
      );

  Map<String, dynamic> toJson() => {
        'match': match,
        'tournament': tournament,
        'team': team,
        'player': player,
        'social': social,
        'system': system,
        'achievement': achievement,
        'marketing': marketing,
        'email_enabled': emailEnabled,
        'push_enabled': pushEnabled,
        'sound': sound,
        'quiet_start': quietStart,
        'quiet_end': quietEnd,
        'tz_offset': tzOffset,
      };

  NotificationPrefs copyWith({
    bool? match,
    bool? tournament,
    bool? team,
    bool? player,
    bool? social,
    bool? system,
    bool? achievement,
    bool? marketing,
    bool? emailEnabled,
    bool? pushEnabled,
    bool? sound,
    int? quietStart,
    int? quietEnd,
    bool clearQuietStart = false,
    bool clearQuietEnd = false,
    int? tzOffset,
  }) =>
      NotificationPrefs(
        match: match ?? this.match,
        tournament: tournament ?? this.tournament,
        team: team ?? this.team,
        player: player ?? this.player,
        social: social ?? this.social,
        system: system ?? this.system,
        achievement: achievement ?? this.achievement,
        marketing: marketing ?? this.marketing,
        emailEnabled: emailEnabled ?? this.emailEnabled,
        pushEnabled: pushEnabled ?? this.pushEnabled,
        sound: sound ?? this.sound,
        quietStart: clearQuietStart ? null : (quietStart ?? this.quietStart),
        quietEnd: clearQuietEnd ? null : (quietEnd ?? this.quietEnd),
        tzOffset: tzOffset ?? this.tzOffset,
      );

  /// Read a category toggle by its key.
  bool byKey(String key) => switch (key) {
        'match' => match,
        'tournament' => tournament,
        'team' => team,
        'player' => player,
        'social' => social,
        'system' => system,
        'achievement' => achievement,
        'marketing' => marketing,
        _ => true,
      };

  NotificationPrefs withKey(String key, bool value) => switch (key) {
        'match' => copyWith(match: value),
        'tournament' => copyWith(tournament: value),
        'team' => copyWith(team: value),
        'player' => copyWith(player: value),
        'social' => copyWith(social: value),
        'system' => copyWith(system: value),
        'achievement' => copyWith(achievement: value),
        'marketing' => copyWith(marketing: value),
        _ => this,
      };
}

class DirectMessage {
  final String id;
  final String senderId;
  final String recipientId;
  final String text;
  final bool isRead;
  final String when;

  /// Did the current viewer send this?
  final bool mine;

  const DirectMessage({
    required this.id,
    this.senderId = '',
    this.recipientId = '',
    this.text = '',
    this.isRead = false,
    this.when = '',
    this.mine = false,
  });

  factory DirectMessage.fromJson(Map<String, dynamic> j) => DirectMessage(
        id: asStr(j['id']),
        senderId: asStr(j['sender_id']),
        recipientId: asStr(j['recipient_id']),
        text: asStr(j['text']),
        isRead: asBool(j['is_read']),
        when: asStr(j['when']),
        mine: asBool(j['mine']),
      );
}

class Conversation {
  final String otherId;
  final String otherName;
  final String lastText;
  final String lastWhen;
  final bool lastMine;
  final int unread;

  const Conversation({
    required this.otherId,
    this.otherName = '',
    this.lastText = '',
    this.lastWhen = '',
    this.lastMine = false,
    this.unread = 0,
  });

  factory Conversation.fromJson(Map<String, dynamic> j) => Conversation(
        otherId: asStr(j['other_id']),
        otherName: asStr(j['other_name']),
        lastText: asStr(j['last_text']),
        lastWhen: asStr(j['last_when']),
        lastMine: asBool(j['last_mine']),
        unread: asInt(j['unread']),
      );

  String get preview => lastMine ? 'You: $lastText' : lastText;
}

class MessageThread {
  final String otherId;
  final String otherName;
  final List<DirectMessage> messages;

  const MessageThread({
    required this.otherId,
    this.otherName = '',
    this.messages = const [],
  });

  factory MessageThread.fromJson(Map<String, dynamic> j) => MessageThread(
        otherId: asStr(j['other_id']),
        otherName: asStr(j['other_name']),
        messages: asMapList(j['messages']).map(DirectMessage.fromJson).toList(),
      );
}

/// A classified on the Looking For board.
class LookingForPost {
  final String id;
  final String authorId;
  final String authorName;

  /// player | team | match
  final String kind;
  final String text;
  final String? location;
  final String? role;

  /// open | closed
  final String status;
  final String when;
  final bool mine;

  const LookingForPost({
    required this.id,
    this.authorId = '',
    this.authorName = '',
    this.kind = 'player',
    this.text = '',
    this.location,
    this.role,
    this.status = 'open',
    this.when = '',
    this.mine = false,
  });

  factory LookingForPost.fromJson(Map<String, dynamic> j) => LookingForPost(
        id: asStr(j['id']),
        authorId: asStr(j['author_id']),
        authorName: asStr(j['author_name']),
        kind: asStr(j['kind'], 'player'),
        text: asStr(j['text']),
        location: asStrOrNull(j['location']),
        role: asStrOrNull(j['role']),
        status: asStr(j['status'], 'open'),
        when: asStr(j['when']),
        mine: asBool(j['mine']),
      );

  bool get isClosed => status == 'closed';

  static const kinds = <String>['player', 'team', 'match'];

  /// What the poster is looking FOR.
  static String kindLabel(String k) => switch (k) {
        'player' => 'Players wanted',
        'team' => 'Team wanted',
        'match' => 'Match wanted',
        _ => k,
      };

  /// How the compose form phrases the choice.
  static String kindPrompt(String k) => switch (k) {
        'player' => 'Players (for my team)',
        'team' => 'A team (I am a player)',
        'match' => 'A match / opponent',
        _ => k,
      };

  String get badge => kindLabel(kind);
}

/// A ground or coaching academy.
class Venue {
  final String id;
  final String name;

  /// ground | academy
  final String kind;
  final String? city;
  final String? address;
  final String? contact;
  final String? note;
  final String when;

  const Venue({
    required this.id,
    this.name = '',
    this.kind = 'ground',
    this.city,
    this.address,
    this.contact,
    this.note,
    this.when = '',
  });

  factory Venue.fromJson(Map<String, dynamic> j) => Venue(
        id: asStr(j['id']),
        name: asStr(j['name']),
        kind: asStr(j['kind'], 'ground'),
        city: asStrOrNull(j['city']),
        address: asStrOrNull(j['address']),
        contact: asStrOrNull(j['contact']),
        note: asStrOrNull(j['note']),
        when: asStr(j['when']),
      );

  static const kinds = <String>['ground', 'academy'];

  static String kindLabel(String k) => k == 'academy' ? 'Academy' : 'Ground';

  bool get isAcademy => kind == 'academy';

  /// "Mumbai · 98765 43210"
  String get subtitle {
    final parts = <String>[
      if (city != null && city!.isNotEmpty) city!,
      if (contact != null && contact!.isNotEmpty) contact!,
    ];
    return parts.isEmpty ? kindLabel(kind) : parts.join(' · ');
  }
}

/// One row on a leaderboard.
class LeaderboardEntry {
  final String playerId;
  final String name;
  final double value;
  final String? detail;

  const LeaderboardEntry({
    required this.playerId,
    this.name = '',
    this.value = 0,
    this.detail,
  });

  factory LeaderboardEntry.fromJson(Map<String, dynamic> j) => LeaderboardEntry(
        playerId: asStr(j['player_id']),
        name: asStr(j['name']),
        value: asDouble(j['value']),
        detail: asStrOrNull(j['detail']),
      );

  /// Whole numbers print without a decimal tail; rates keep two places.
  String get valueText =>
      value == value.roundToDouble() ? value.toInt().toString() : value.toStringAsFixed(2);
}

/// One named board with its rows.
class LeaderboardBoard {
  final String key;
  final String title;
  final List<LeaderboardEntry> entries;

  const LeaderboardBoard({
    required this.key,
    required this.title,
    this.entries = const [],
  });

  bool get isEmpty => entries.isEmpty;
}

class Leaderboards {
  final int minInnings;

  /// all | week | month | year | custom
  final String window;
  final String? location;
  final List<String> locations;
  final List<LeaderboardBoard> boards;

  const Leaderboards({
    this.minInnings = 1,
    this.window = 'all',
    this.location,
    this.locations = const [],
    this.boards = const [],
  });

  /// The 12 boards, in the order the website shows them.
  static const boardOrder = <String, String>{
    'mvp': 'MVP — all-rounders',
    'most_runs': 'Most runs',
    'most_wickets': 'Most wickets',
    'highest_score': 'Highest score',
    'best_bowling': 'Best bowling (innings)',
    'most_catches': 'Most catches',
    'best_average': 'Best batting average',
    'best_strike_rate': 'Best strike rate',
    'best_economy': 'Best economy',
    'best_bowling_average': 'Best bowling average',
    'most_sixes': 'Most sixes',
    'most_fours': 'Most fours',
  };

  static const windows = <String, String>{
    'all': 'All time',
    'year': 'This year',
    'month': 'This month',
    'week': 'This week',
  };

  factory Leaderboards.fromJson(Map<String, dynamic> j) {
    final boards = <LeaderboardBoard>[];
    boardOrder.forEach((key, title) {
      final rows = asMapList(j[key]).map(LeaderboardEntry.fromJson).toList();
      boards.add(LeaderboardBoard(key: key, title: title, entries: rows));
    });
    return Leaderboards(
      minInnings: asInt(j['min_innings'], 1),
      window: asStr(j['window'], 'all'),
      location: asStrOrNull(j['location']),
      locations: asStrList(j['locations']),
      boards: boards,
    );
  }

  List<LeaderboardBoard> get nonEmptyBoards =>
      boards.where((b) => b.entries.isNotEmpty).toList();

  bool get isEmpty => nonEmptyBoards.isEmpty;
}

/// Unified search across every entity type.
class SearchResults {
  final String query;
  final List<Player> players;
  final List<Team> teams;
  final List<TournamentSummary> tournaments;

  /// Only populated when a valid token is sent.
  final List<PublicUser> members;
  final List<Venue> venues;

  const SearchResults({
    this.query = '',
    this.players = const [],
    this.teams = const [],
    this.tournaments = const [],
    this.members = const [],
    this.venues = const [],
  });

  factory SearchResults.fromJson(Map<String, dynamic> j) => SearchResults(
        query: asStr(j['query']),
        players: asMapList(j['players']).map(Player.fromJson).toList(),
        teams: asMapList(j['teams']).map(Team.fromJson).toList(),
        tournaments:
            asMapList(j['tournaments']).map(TournamentSummary.fromJson).toList(),
        members: asMapList(j['members']).map(PublicUser.fromJson).toList(),
        venues: asMapList(j['venues']).map(Venue.fromJson).toList(),
      );

  bool get isEmpty =>
      players.isEmpty &&
      teams.isEmpty &&
      tournaments.isEmpty &&
      members.isEmpty &&
      venues.isEmpty;

  int get total =>
      players.length +
      teams.length +
      tournaments.length +
      members.length +
      venues.length;
}
