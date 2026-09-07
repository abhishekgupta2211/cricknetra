/// Reads behind the admin role-management screens.
///
/// Every one is `autoDispose`: role work happens in short bursts, and a cached
/// organizer list that outlives the visit is exactly the kind of stale data
/// somebody acts on by mistake — suspending a person who was already removed.
///
/// The server refuses all of these to anybody but an admin. The screens gate on
/// `AuthState.isAdmin` as well, so a non-admin sees an explanation rather than a
/// spinner that ends in 403.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/org.dart';
import '../../core/models/user.dart';

final areasProvider = FutureProvider.autoDispose<List<Area>>(
  (ref) => ref.watch(apiProvider).areas(),
);

final organizationsProvider = FutureProvider.autoDispose<List<Organization>>(
  (ref) => ref.watch(apiProvider).organizations(),
);

/// Organizers, narrowed to one area when an id is given and every area on null.
final organizersProvider =
    FutureProvider.autoDispose.family<List<Organizer>, String?>(
  (ref, areaId) => ref.watch(apiProvider).organizers(areaId: areaId),
);

/// The audit trail for one action, or all of them on null.
///
/// The server already answers newest-first; sorting again costs nothing and
/// means the screen's promise holds even if a future store returns insertion
/// order. Entries with no timestamp sink to the bottom rather than jumping to
/// the top, where they would read as "just happened".
final auditTrailProvider =
    FutureProvider.autoDispose.family<List<AuditEntry>, String?>(
  (ref, action) async {
    final rows = await ref.watch(apiProvider).auditTrail(
          limit: 200,
          action: action,
        );
    final sorted = [...rows];
    sorted.sort((a, b) {
      final ta = DateTime.tryParse(a.when ?? '');
      final tb = DateTime.tryParse(b.when ?? '');
      if (ta == null && tb == null) return 0;
      if (ta == null) return 1;
      if (tb == null) return -1;
      return tb.compareTo(ta);
    });
    return sorted;
  },
);

/// Every account, for the organizer picker and the role sheet.
///
/// The admin screens promote people who already have accounts, so this is the
/// pool both pickers search — there is no second way to create a login.
final allUsersProvider = FutureProvider.autoDispose<List<PublicUser>>(
  (ref) => ref.watch(apiProvider).users(),
);

/// The roles an admin may grant, mirroring `Roles.ASSIGNABLE` on the server.
///
/// Kept here rather than in [Roles] because it is an admin-console concern:
/// sign-up offers a different, smaller list, and the server rejects anything
/// outside this one with the list it does accept.
const assignableRoles = <String>[
  Roles.generalUser,
  Roles.player,
  Roles.teamOwner,
  Roles.umpire,
  Roles.commentator,
  Roles.organizer,
  Roles.admin,
];

/// Actions worth filtering the audit trail by, newest concerns first.
///
/// A short list beats every action the server has ever written: the point of
/// the filter is to answer "who changed authority", not to enumerate the log.
const auditActionFilters = <({String? value, String label})>[
  (value: null, label: 'Everything'),
  (value: 'role.assigned', label: 'Roles'),
  (value: 'organizer.created', label: 'Organizers added'),
  (value: 'organizer.deactivated', label: 'Organizers removed'),
  (value: 'tournament.deleted', label: 'Tournaments deleted'),
  (value: 'match.deleted', label: 'Matches deleted'),
  (value: 'access.denied', label: 'Refused'),
];

/// Re-read everything the admin section shows.
///
/// A single write ripples: promoting somebody changes the organizer list, the
/// area's counts and the audit trail at once, so screens invalidate the set
/// rather than guessing which of the three the user is looking at.
void invalidateAdminReads(WidgetRef ref) {
  ref.invalidate(areasProvider);
  ref.invalidate(organizationsProvider);
  ref.invalidate(organizersProvider);
  ref.invalidate(allUsersProvider);
  ref.invalidate(auditTrailProvider);
}
