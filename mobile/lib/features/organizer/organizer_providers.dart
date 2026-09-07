/// Reads behind the organizer's desk and the staff screens.
///
/// Everything here is a read. The writes (`addUmpire`, `removeStaff`,
/// `setStaffActive`) stay on the screens that own the button, because each one
/// has to report the server's own refusal — a 409 explaining that adding
/// somebody would take a role away is the useful part of that call, and a
/// provider that swallowed it into an AsyncError would lose the sentence.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/org.dart';
import '../../core/models/tournament.dart';
import '../../core/models/user.dart';

/// The competitions on the dashboard.
///
/// `GET /tournaments` is the public list — the server does not narrow it to the
/// caller — so the screens behind each card are where ownership actually bites:
/// staff and roster are scoped to the owning organizer, the people assigned to
/// that competition, and the admin. Anybody else is refused there by the
/// server rather than quietly filtered out here.
final organizerTournamentsProvider =
    FutureProvider.autoDispose<List<TournamentSummary>>(
  (ref) => ref.watch(apiProvider).tournaments(),
);

/// One competition's umpires and commentators, stood-down entries included.
///
/// The server deliberately returns the inactive ones too: an organizer who
/// stood somebody down still has to see them, or the only way back is to
/// remember the name and add them again.
final tournamentStaffProvider =
    FutureProvider.autoDispose.family<List<TournamentStaff>, String>(
  (ref, tournamentId) => ref.watch(apiProvider).tournamentStaff(tournamentId),
);

/// The competitions the signed-in user is staff on.
///
/// The server reads the person from the token, so there is nothing to pass and
/// nothing to tamper with — this can only ever answer for the caller.
final myStaffingProvider =
    FutureProvider.autoDispose<List<MyStaffing>>((ref) async {
  if (!ref.watch(isSignedInProvider)) return const [];
  return ref.watch(apiProvider).myStaffing();
});

/// Everybody registered across a competition's squads, already flattened.
final tournamentPlayersProvider =
    FutureProvider.autoDispose.family<List<TournamentPlayer>, String>(
  (ref, tournamentId) => ref.watch(apiProvider).tournamentPlayers(tournamentId),
);

/// The directory, for the "add somebody to the staff" picker.
///
/// `/users` has no query parameter, so the picker filters this list in memory.
/// For a local league that is the whole roster and one round trip; a request
/// per keystroke would be slower and no more correct.
final directoryUsersProvider = FutureProvider.autoDispose<List<PublicUser>>(
  (ref) => ref.watch(apiProvider).users(),
);

/// The signed-in organizer's own area and organization, or null.
///
/// Best-effort on purpose: the posting lives on the admin's organizer roster
/// and nowhere else — `/auth/me` does not carry it, and `/admin/organizers`
/// answers 403 to anyone but an admin. So this is a decoration that either
/// resolves or does not, and a failure must never take the dashboard with it.
final myOrganizerProvider =
    FutureProvider.autoDispose<Organizer?>((ref) async {
  final user = ref.watch(currentUserProvider);
  if (user == null) return null;
  try {
    final roster = await ref.watch(apiProvider).organizers();
    for (final o in roster) {
      if (o.userId == user.id) return o;
    }
    return null;
  } catch (_) {
    return null;
  }
});

/// Staff split into the two groups the screen shows, in a fixed order so the
/// page does not reshuffle when somebody is added.
({List<TournamentStaff> umpires, List<TournamentStaff> commentators})
    groupStaff(List<TournamentStaff> staff) => (
          umpires: [
            for (final s in staff)
              if (s.staffRole == TournamentStaff.umpire) s,
          ],
          commentators: [
            for (final s in staff)
              if (s.staffRole == TournamentStaff.commentator) s,
          ],
        );

/// Assignments grouped by the job, umpiring first.
///
/// Somebody can be both on different competitions, and mixing the two into one
/// list loses which hat they are wearing where.
List<({String role, List<MyStaffing> entries})> groupStaffing(
  List<MyStaffing> staffing,
) {
  const order = [TournamentStaff.umpire, TournamentStaff.commentator];
  final out = <({String role, List<MyStaffing> entries})>[];
  for (final role in order) {
    final entries = [
      for (final s in staffing)
        if (s.staffRole == role) s,
    ];
    if (entries.isNotEmpty) out.add((role: role, entries: entries));
  }
  // Anything the server invents later still gets a section rather than
  // vanishing from a screen that is somebody's whole view of the product.
  for (final s in staffing) {
    if (order.contains(s.staffRole)) continue;
    final at = out.indexWhere((g) => g.role == s.staffRole);
    if (at == -1) {
      out.add((role: s.staffRole, entries: [s]));
    } else {
      out[at].entries.add(s);
    }
  }
  return out;
}
