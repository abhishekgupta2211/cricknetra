/// Organizers, and the areas and organizations they run competitions for.
///
/// An **area** is a place ("Prayagraj"); an **organization** is a body that
/// runs cricket there; an **organizer** is an account tied to both. Admin owns
/// all three — an organizer reads them and never writes them.
library;

import 'json.dart';
import 'roster.dart';

class Area {
  final String id;
  final String name;
  final String? state;

  /// How many organizers work here, and how many competitions they run.
  final int organizers;
  final int tournaments;

  const Area({
    required this.id,
    required this.name,
    this.state,
    this.organizers = 0,
    this.tournaments = 0,
  });

  factory Area.fromJson(Map<String, dynamic> j) => Area(
        id: asStr(j['id']),
        name: asStr(j['name']),
        state: asStrOrNull(j['state']),
        organizers: asInt(j['organizers']),
        tournaments: asInt(j['tournaments']),
      );

  /// "Prayagraj · Uttar Pradesh"
  String get title => [name, ?state].join(' · ');
}

class Organization {
  final String id;
  final String name;
  final String? areaId;
  final String? areaName;

  const Organization({
    required this.id,
    required this.name,
    this.areaId,
    this.areaName,
  });

  factory Organization.fromJson(Map<String, dynamic> j) => Organization(
        id: asStr(j['id']),
        name: asStr(j['name']),
        areaId: asStrOrNull(j['area_id']),
        areaName: asStrOrNull(j['area_name']),
      );
}

/// One user's standing as an organizer.
class Organizer {
  final String userId;
  final String fullName;
  final String username;
  final String mobileNo;
  final String role;

  /// A suspended organizer keeps the role but cannot act, so they can be stood
  /// down for a season without being demoted.
  final bool isActive;

  final String? areaId;
  final String? areaName;
  final String? organizationId;
  final String? organizationName;

  /// How many competitions they own.
  final int tournaments;
  final String? createdAt;

  const Organizer({
    required this.userId,
    this.fullName = '',
    this.username = '',
    this.mobileNo = '',
    this.role = '',
    this.isActive = true,
    this.areaId,
    this.areaName,
    this.organizationId,
    this.organizationName,
    this.tournaments = 0,
    this.createdAt,
  });

  factory Organizer.fromJson(Map<String, dynamic> j) => Organizer(
        userId: asStr(j['user_id']),
        fullName: asStr(j['full_name']),
        username: asStr(j['username']),
        mobileNo: asStr(j['mobile_no']),
        role: asStr(j['role']),
        isActive: asBool(j['is_active'], true),
        areaId: asStrOrNull(j['area_id']),
        areaName: asStrOrNull(j['area_name']),
        organizationId: asStrOrNull(j['organization_id']),
        organizationName: asStrOrNull(j['organization_name']),
        tournaments: asInt(j['tournaments']),
        createdAt: asStrOrNull(j['created_at']),
      );

  String get displayName => fullName.isNotEmpty ? fullName : username;

  /// "XYZ Sports · Prayagraj", or whichever half is known.
  String get posting => [
        ?organizationName,
        ?areaName,
      ].join(' · ');
}

/// An umpire or commentator on one competition's staff.
///
/// Scoped to a single tournament: somebody Organizer A adds does not become
/// available to Organizer B, who adds them to their own competition through a
/// second, independent entry.
class TournamentStaff {
  final String userId;
  final String fullName;
  final String username;
  final String mobileNo;

  /// umpire | commentator
  final String staffRole;
  final bool isActive;
  final String tournamentId;
  final String? addedBy;

  const TournamentStaff({
    required this.userId,
    this.fullName = '',
    this.username = '',
    this.mobileNo = '',
    this.staffRole = '',
    this.isActive = true,
    this.tournamentId = '',
    this.addedBy,
  });

  factory TournamentStaff.fromJson(Map<String, dynamic> j) => TournamentStaff(
        userId: asStr(j['user_id']),
        fullName: asStr(j['full_name']),
        username: asStr(j['username']),
        mobileNo: asStr(j['mobile_no']),
        staffRole: asStr(j['staff_role']),
        isActive: asBool(j['is_active'], true),
        tournamentId: asStr(j['tournament_id']),
        addedBy: asStrOrNull(j['added_by']),
      );

  String get displayName => fullName.isNotEmpty ? fullName : username;

  static const umpire = 'umpire';
  static const commentator = 'commentator';

  static String label(String role) => switch (role) {
        umpire => 'Umpire',
        commentator => 'Commentator',
        _ => role,
      };
}

/// A competition the signed-in user is staff on, for their own dashboard.
class MyStaffing {
  final String tournamentId;
  final String tournamentName;
  final String staffRole;
  final bool isActive;

  const MyStaffing({
    required this.tournamentId,
    this.tournamentName = '',
    this.staffRole = '',
    this.isActive = true,
  });

  factory MyStaffing.fromJson(Map<String, dynamic> j) => MyStaffing(
        tournamentId: asStr(j['tournament_id']),
        tournamentName: asStr(j['tournament_name']),
        staffRole: asStr(j['staff_role']),
        isActive: asBool(j['is_active'], true),
      );
}

/// One player registered in a competition, with the team they play for.
class TournamentPlayer {
  final String teamId;
  final String teamName;
  final Player player;

  const TournamentPlayer({
    required this.teamId,
    required this.teamName,
    required this.player,
  });

  factory TournamentPlayer.fromJson(Map<String, dynamic> j) => TournamentPlayer(
        teamId: asStr(j['team_id']),
        teamName: asStr(j['team_name']),
        player: Player.fromJson(asMap(j['player'])),
      );
}

/// One line of the audit trail — who changed what, and when.
class AuditEntry {
  final String id;
  final String? actorId;
  final String actorName;
  final String action;
  final String resourceType;
  final String resourceId;
  final String detail;
  final String? when;

  const AuditEntry({
    required this.id,
    this.actorId,
    this.actorName = '',
    this.action = '',
    this.resourceType = '',
    this.resourceId = '',
    this.detail = '',
    this.when,
  });

  factory AuditEntry.fromJson(Map<String, dynamic> j) => AuditEntry(
        id: asStr(j['id']),
        actorId: asStrOrNull(j['actor_id']),
        actorName: asStr(j['actor_name']),
        action: asStr(j['action']),
        resourceType: asStr(j['resource_type']),
        resourceId: asStr(j['resource_id']),
        detail: asStr(j['detail']),
        when: asStrOrNull(j['when']),
      );

  /// "Role assigned" from "role.assigned".
  String get label {
    if (action.isEmpty) return '';
    final words = action.replaceAll('.', ' ').replaceAll('_', ' ');
    return words[0].toUpperCase() + words.substring(1);
  }

  /// Actions that move authority or destroy data are worth flagging.
  bool get isWeighty =>
      action.endsWith('.deleted') ||
      action == 'role.assigned' ||
      action.startsWith('organizer.');
}
