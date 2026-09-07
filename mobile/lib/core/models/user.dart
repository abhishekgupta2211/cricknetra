/// Accounts, roles, capabilities and the extended profile.
library;

import 'json.dart';

/// Capability strings the server grants per role. The UI shows or hides
/// creation actions to match `ROLE_CAPABILITIES` in the backend.
/// Mirrors `backend/app/core/permissions.py :: Caps`.
///
/// A capability says what *kind* of thing a role may do. It never says whose:
/// two organizers both hold [manageTournament] and neither may touch the
/// other's competition. The server decides that from ownership; these strings
/// only let the app hide what the server would refuse.
class Caps {
  const Caps._();
  static const createMatch = 'match.create';
  static const scoreMatch = 'match.score';
  static const commentate = 'match.commentate';
  static const createTeam = 'team.create';
  static const managePlayers = 'player.manage';
  static const createTournament = 'tournament.create';
  static const manageTournament = 'tournament.manage';
  static const deleteTournament = 'tournament.delete';
  static const manageUmpires = 'umpire.manage';
  static const manageCommentators = 'commentator.manage';
  static const manageRules = 'rules.manage';
  static const manageUsers = 'user.manage';
  static const manageOrganizers = 'organizer.manage';

  static const all = <String>[
    createMatch,
    scoreMatch,
    commentate,
    createTeam,
    managePlayers,
    createTournament,
    manageTournament,
    deleteTournament,
    manageUmpires,
    manageCommentators,
    manageRules,
    manageUsers,
    manageOrganizers,
  ];

  static String label(String cap) => switch (cap) {
        createMatch => 'Score matches',
        scoreMatch => 'Officiate any match',
        commentate => 'Post live commentary',
        createTeam => 'Manage teams & players',
        managePlayers => 'Add players to your tournaments',
        createTournament => 'Organize tournaments',
        manageTournament => 'Run your tournaments',
        deleteTournament => 'Delete your tournaments',
        manageUmpires => 'Appoint umpires',
        manageCommentators => 'Appoint commentators',
        manageRules => 'Build rule templates',
        manageUsers => 'Assign roles',
        manageOrganizers => 'Manage organizers',
        _ => cap,
      };
}

/// Account roles, mirroring the server.
class Roles {
  const Roles._();
  static const player = 'player';
  static const umpire = 'umpire';
  static const commentator = 'commentator';
  static const organizer = 'organizer';
  static const teamOwner = 'team_owner';
  static const admin = 'admin';
  static const generalUser = 'general_user';

  /// Every account is created here. A role is granted by an admin after
  /// looking at the person — never chosen by a stranger at sign-up, or anyone
  /// could register as an organizer and start running competitions.
  static const signupRole = generalUser;

  /// Roles whose access comes from being assigned to a competition rather than
  /// from the role itself.
  static const assignmentScoped = <String>{umpire, commentator};

  /// What the sign-up form may ask to become. This is a *request* an admin
  /// acts on; the account is a general user either way.
  static const signupChoices = <String>[
    player,
    teamOwner,
    organizer,
    umpire,
    commentator,
  ];

  /// The tabs of the member directory.
  static const directoryRoles = <String>[
    player,
    umpire,
    commentator,
    organizer,
    teamOwner,
  ];

  static String label(String role) => switch (role) {
        player => 'Player',
        umpire => 'Umpire',
        commentator => 'Commentator',
        organizer => 'Organizer',
        teamOwner => 'Team owner',
        admin => 'Admin',
        generalUser => 'General user',
        _ => role.replaceAll('_', ' '),
      };

  static String plural(String role) => switch (role) {
        player => 'Players',
        umpire => 'Umpires',
        commentator => 'Commentators',
        organizer => 'Organizers',
        teamOwner => 'Team owners',
        _ => '${label(role)}s',
      };

  static String blurb(String role) => switch (role) {
        player => 'Track your career stats and claim your profile.',
        generalUser => 'Follow matches and browse everything.',
        teamOwner => 'Create and manage teams. Needs admin approval.',
        organizer => 'Run tournaments and score matches. Needs admin approval.',
        umpire => 'Officiate matches you are approved for. Needs admin approval.',
        commentator => 'Post live commentary. Needs admin approval.',
        _ => '',
      };
}

/// A member's activity tally.
class MemberRecords {
  final int matchesScored;
  final int matchesUmpired;
  final int matchesCommentated;
  final int tournamentsOrganized;
  final int teamsOwned;

  const MemberRecords({
    this.matchesScored = 0,
    this.matchesUmpired = 0,
    this.matchesCommentated = 0,
    this.tournamentsOrganized = 0,
    this.teamsOwned = 0,
  });

  factory MemberRecords.fromJson(Map<String, dynamic> j) => MemberRecords(
        matchesScored: asInt(j['matches_scored']),
        matchesUmpired: asInt(j['matches_umpired']),
        matchesCommentated: asInt(j['matches_commentated']),
        tournamentsOrganized: asInt(j['tournaments_organized']),
        teamsOwned: asInt(j['teams_owned']),
      );

  /// The headline record for a given role, the way the directory shows it.
  String lineFor(String role) => switch (role) {
        Roles.umpire => '$matchesUmpired matches officiated',
        Roles.commentator => '$matchesCommentated commentated',
        Roles.organizer => '$tournamentsOrganized tournaments organized',
        Roles.teamOwner => '$teamsOwned teams',
        _ => '$matchesScored matches scored',
      };
}

/// The signed-in account, from `GET /auth/me`.
class AppUser {
  final String id;
  final String fullName;
  final String username;
  final String mobileNo;
  final String? email;
  final String userCode;
  final String roleCode;
  final String role;
  final bool isActive;
  final bool isVerified;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final List<String> capabilities;
  final MemberRecords records;
  final bool hasPhoto;

  /// True while an elevated role awaits admin approval.
  final bool rolePending;
  final String? requestedRole;

  const AppUser({
    required this.id,
    this.fullName = '',
    this.username = '',
    this.mobileNo = '',
    this.email,
    this.userCode = '',
    this.roleCode = '',
    this.role = Roles.generalUser,
    this.isActive = true,
    this.isVerified = false,
    this.createdAt,
    this.updatedAt,
    this.capabilities = const [],
    this.records = const MemberRecords(),
    this.hasPhoto = false,
    this.rolePending = false,
    this.requestedRole,
  });

  factory AppUser.fromJson(Map<String, dynamic> j) => AppUser(
        id: asStr(j['id']),
        fullName: asStr(j['full_name']),
        username: asStr(j['username']),
        mobileNo: asStr(j['mobile_no']),
        email: asStrOrNull(j['email']),
        userCode: asStr(j['user_code']),
        roleCode: asStr(j['role_code']),
        role: asStr(j['role'], Roles.generalUser),
        isActive: asBool(j['is_active'], true),
        isVerified: asBool(j['is_verified']),
        createdAt: asDate(j['created_at']),
        updatedAt: asDate(j['updated_at']),
        capabilities: asStrList(j['capabilities']),
        records: MemberRecords.fromJson(asMap(j['records'])),
        hasPhoto: asBool(j['has_photo']),
        rolePending: asBool(j['role_pending']),
        requestedRole: asStrOrNull(j['requested_role']),
      );

  bool get isAdmin => role == Roles.admin;

  bool can(String capability) => capabilities.contains(capability);

  /// First name, for greetings.
  String get firstName {
    final trimmed = fullName.trim();
    if (trimmed.isEmpty) return username;
    final space = trimmed.indexOf(' ');
    return space > 0 ? trimmed.substring(0, space) : trimmed;
  }

  String get displayName => fullName.isNotEmpty ? fullName : username;
}

/// A member as shown in the directory and search — safe fields only.
class PublicUser {
  final String id;
  final String fullName;
  final String username;
  final String role;
  final String roleCode;
  final String userCode;
  final String mobileNo;
  final bool isVerified;
  final String? location;
  final MemberRecords records;
  final bool hasPhoto;

  const PublicUser({
    required this.id,
    this.fullName = '',
    this.username = '',
    this.role = Roles.generalUser,
    this.roleCode = '',
    this.userCode = '',
    this.mobileNo = '',
    this.isVerified = false,
    this.location,
    this.records = const MemberRecords(),
    this.hasPhoto = false,
  });

  factory PublicUser.fromJson(Map<String, dynamic> j) => PublicUser(
        id: asStr(j['id']),
        fullName: asStr(j['full_name']),
        username: asStr(j['username']),
        role: asStr(j['role'], Roles.generalUser),
        roleCode: asStr(j['role_code']),
        userCode: asStr(j['user_code']),
        mobileNo: asStr(j['mobile_no']),
        isVerified: asBool(j['is_verified']),
        location: asStrOrNull(j['location']),
        records: MemberRecords.fromJson(asMap(j['records'])),
        hasPhoto: asBool(j['has_photo']),
      );

  /// "@rohit · Mumbai"
  String get handleLine {
    final base = '@$username';
    return location == null || location!.isEmpty ? base : '$base · $location';
  }

  String get recordLine => records.lineFor(role);
}

/// A pending elevated-role sign-up, for the admin queue.
class RoleRequest {
  final String userId;
  final String fullName;
  final String username;
  final String requestedRole;
  final String when;

  const RoleRequest({
    required this.userId,
    this.fullName = '',
    this.username = '',
    this.requestedRole = '',
    this.when = '',
  });

  factory RoleRequest.fromJson(Map<String, dynamic> j) => RoleRequest(
        userId: asStr(j['user_id']),
        fullName: asStr(j['full_name']),
        username: asStr(j['username']),
        requestedRole: asStr(j['requested_role']),
        when: asStr(j['when']),
      );
}

/// The extended profile from `GET /auth/profile`.
class UserProfile {
  final String id;
  final String userId;
  final String address;
  final String pincode;
  final String city;
  final String district;
  final String state;
  final String region;
  final String? profilePicture;

  const UserProfile({
    required this.id,
    this.userId = '',
    this.address = '',
    this.pincode = '',
    this.city = '',
    this.district = '',
    this.state = '',
    this.region = '',
    this.profilePicture,
  });

  factory UserProfile.fromJson(Map<String, dynamic> j) => UserProfile(
        id: asStr(j['id']),
        userId: asStr(j['user_id']),
        address: asStr(j['address']),
        pincode: asStr(j['pincode']),
        city: asStr(j['city']),
        district: asStr(j['district']),
        state: asStr(j['state']),
        region: asStr(j['region']),
        profilePicture: asStrOrNull(j['profile_picture']),
      );

  Map<String, dynamic> toJson() => {
        'address': address,
        'pincode': pincode,
        'city': city,
        'district': district,
        'state': state,
        'region': region,
      };
}

/// An admin broadcast, with its engagement numbers.
class AnnouncementCampaign {
  final String id;
  final String title;
  final String text;
  final String category;
  final String link;
  final int recipients;
  final String when;
  final int delivered;
  final int opened;
  final int clicked;
  final double openRate;
  final double ctr;

  const AnnouncementCampaign({
    required this.id,
    this.title = '',
    this.text = '',
    this.category = 'system',
    this.link = '',
    this.recipients = 0,
    this.when = '',
    this.delivered = 0,
    this.opened = 0,
    this.clicked = 0,
    this.openRate = 0,
    this.ctr = 0,
  });

  factory AnnouncementCampaign.fromJson(Map<String, dynamic> j) =>
      AnnouncementCampaign(
        id: asStr(j['id']),
        title: asStr(j['title']),
        text: asStr(j['text']),
        category: asStr(j['category'], 'system'),
        link: asStr(j['link']),
        recipients: asInt(j['recipients']),
        when: asStr(j['when']),
        delivered: asInt(j['delivered']),
        opened: asInt(j['opened']),
        clicked: asInt(j['clicked']),
        openRate: asDouble(j['open_rate']),
        ctr: asDouble(j['ctr']),
      );
}
