/// The working view of one competition: who officiates it, and who plays in it.
///
/// Both screens live in one file because they are one scope — the server lets
/// the owning organizer, the people assigned to the competition and the admin
/// read either, and refuses everybody else — and because splitting them would
/// duplicate the same header, the same gate and the same error handling twice.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_config.dart';
import '../../core/api/api_exception.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/org.dart';
import '../../core/models/user.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../tournaments/tournament_providers.dart';
import 'organizer_providers.dart';

/// The umpires and commentators on one competition.
class TournamentStaffScreen extends ConsumerWidget {
  final String tournamentId;

  const TournamentStaffScreen({super.key, required this.tournamentId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(tournamentStaffProvider(tournamentId));
    final staff = async.valueOrNull;
    final auth = ref.watch(authControllerProvider);

    // A UX check only. These capabilities say the account may appoint officials
    // *somewhere*; they say nothing about this competition. The server decides
    // that from who owns it, so a different organizer holding exactly these
    // capabilities is still refused. Hiding the buttons only saves a wasted tap.
    final canManageUmpires = auth.can(Caps.manageUmpires);
    final canManageCommentators = auth.can(Caps.manageCommentators);

    return Scaffold(
      appBar: _CompetitionAppBar(tournamentId: tournamentId, title: 'Staff'),
      // Errors render here, inside the Scaffold, so the app bar and its back
      // arrow survive a 403 or a dead connection.
      body: staff == null && async.hasError
          ? ErrorState(
              error: async.error!,
              onRetry: () =>
                  ref.invalidate(tournamentStaffProvider(tournamentId)),
            )
          : RefreshIndicator(
              onRefresh: () async =>
                  ref.invalidate(tournamentStaffProvider(tournamentId)),
              child: staff == null
                  ? const Padding(
                      padding: EdgeInsets.all(16),
                      child: ListSkeleton(rows: 4),
                    )
                  : _StaffList(
                      tournamentId: tournamentId,
                      staff: staff,
                      canManageUmpires: canManageUmpires,
                      canManageCommentators: canManageCommentators,
                    ),
            ),
    );
  }
}

class _StaffList extends StatelessWidget {
  final String tournamentId;
  final List<TournamentStaff> staff;
  final bool canManageUmpires;
  final bool canManageCommentators;

  const _StaffList({
    required this.tournamentId,
    required this.staff,
    required this.canManageUmpires,
    required this.canManageCommentators,
  });

  @override
  Widget build(BuildContext context) {
    final groups = groupStaff(staff);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
      children: [
        CnCard(
          color: context.cric.surfaceVariant,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.info_outline, size: 18, color: context.cric.muted),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Staff are appointed per competition. Taking somebody off '
                  'here ends their job on this competition only — their '
                  'account, their role and their work on anybody else’s '
                  'competition are untouched.',
                  style: context.texts.bodySmall,
                ),
              ),
            ],
          ),
        ),
        _StaffGroup(
          tournamentId: tournamentId,
          staffRole: TournamentStaff.umpire,
          title: 'Umpires',
          members: groups.umpires,
          canManage: canManageUmpires,
        ),
        _StaffGroup(
          tournamentId: tournamentId,
          staffRole: TournamentStaff.commentator,
          title: 'Commentators',
          members: groups.commentators,
          canManage: canManageCommentators,
        ),
      ],
    );
  }
}

class _StaffGroup extends ConsumerWidget {
  final String tournamentId;
  final String staffRole;
  final String title;
  final List<TournamentStaff> members;
  final bool canManage;

  const _StaffGroup({
    required this.tournamentId,
    required this.staffRole,
    required this.title,
    required this.members,
    required this.canManage,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final label = TournamentStaff.label(staffRole).toLowerCase();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionHeader(
          title: title,
          trailing: Text('${members.length}', style: context.texts.labelLarge),
        ),
        if (members.isEmpty)
          CnCard(
            child: Text(
              'No $label on this competition yet.',
              style: context.texts.bodySmall,
            ),
          )
        else
          for (final m in members)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _StaffRow(
                tournamentId: tournamentId,
                member: m,
                canManage: canManage,
              ),
            ),
        if (canManage) ...[
          const SizedBox(height: 4),
          OutlinedButton.icon(
            onPressed: () => _add(context, ref),
            icon: const Icon(Icons.person_add_alt, size: 17),
            label: Text('Add $label'),
          ),
        ],
      ],
    );
  }

  Future<void> _add(BuildContext context, WidgetRef ref) async {
    final picked = await showModalBottomSheet<PublicUser>(
      context: context,
      isScrollControlled: true,
      builder: (context) => _PickPersonSheet(
        staffRole: staffRole,
        alreadyOn: {for (final m in members) m.userId},
      ),
    );
    if (picked == null || !context.mounted) return;

    final api = ref.read(apiProvider);
    try {
      if (staffRole == TournamentStaff.umpire) {
        await api.addUmpire(tournamentId, picked.id);
      } else {
        await api.addCommentator(tournamentId, picked.id);
      }
      ref.invalidate(tournamentStaffProvider(tournamentId));
    } on ApiException catch (e) {
      if (!context.mounted) return;
      // A 409 here is not a failure to shrug at and retry: the server is
      // explaining that this person already holds a role, and that adding them
      // would take it away. That sentence is the whole answer, so it gets a
      // dialog and is shown exactly as sent — a generic "Something went wrong"
      // would throw away the only part worth reading.
      if (e.isConflict) {
        await showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Cannot add them'),
            content: Text(e.message),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      } else {
        context.toastError(e);
      }
    } catch (e) {
      if (context.mounted) context.toastError(e);
    }
  }
}

/// One person on the staff, with the two things an organizer does to them.
class _StaffRow extends ConsumerWidget {
  final String tournamentId;
  final TournamentStaff member;
  final bool canManage;

  const _StaffRow({
    required this.tournamentId,
    required this.member,
    required this.canManage,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final subtitle = [
      if (member.username.isNotEmpty) '@${member.username}',
      if (member.mobileNo.isNotEmpty) member.mobileNo,
    ].join(' · ');

    return CnCard(
      padding: const EdgeInsets.fromLTRB(14, 10, 6, 10),
      child: Row(
        children: [
          CnAvatar(name: member.displayName, size: 36),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  member.displayName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
                if (subtitle.isNotEmpty)
                  Text(
                    subtitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.texts.bodySmall,
                  ),
                if (!member.isActive) ...[
                  const SizedBox(height: 4),
                  CnBadge(text: 'Stood down', color: context.cric.amber),
                ],
              ],
            ),
          ),
          if (canManage)
            // A menu rather than a switch plus a button: at 375px two trailing
            // controls squeeze the name into an ellipsis.
            PopupMenuButton<String>(
              icon: Icon(Icons.more_vert, size: 20, color: context.cric.muted),
              onSelected: (value) => switch (value) {
                'active' => _setActive(context, ref, !member.isActive),
                _ => _remove(context, ref),
              },
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: 'active',
                  child: Text(
                    member.isActive ? 'Stand down' : 'Bring back',
                  ),
                ),
                const PopupMenuItem(
                  value: 'remove',
                  child: Text('Take off this competition'),
                ),
              ],
            ),
        ],
      ),
    );
  }

  Future<void> _setActive(
    BuildContext context,
    WidgetRef ref,
    bool active,
  ) async {
    try {
      await ref.read(apiProvider).setStaffActive(
            tournamentId,
            member.staffRole,
            member.userId,
            active,
          );
      ref.invalidate(tournamentStaffProvider(tournamentId));
    } catch (e) {
      if (context.mounted) context.toastError(e);
    }
  }

  Future<void> _remove(BuildContext context, WidgetRef ref) async {
    final role = TournamentStaff.label(member.staffRole).toLowerCase();
    final ok = await confirmDialog(
      context,
      title: 'Take them off this competition?',
      message: '${member.displayName} stops being $role here. This does not '
          'delete their account or their role, and it leaves their work on '
          'every other organizer’s competition alone.',
      confirmLabel: 'Take off',
    );
    if (!ok || !context.mounted) return;
    try {
      await ref
          .read(apiProvider)
          .removeStaff(tournamentId, member.staffRole, member.userId);
      ref.invalidate(tournamentStaffProvider(tournamentId));
      if (context.mounted) {
        context.toast('${member.displayName} is off this competition');
      }
    } catch (e) {
      if (context.mounted) context.toastError(e);
    }
  }
}

/// Pick an existing account to put on the staff.
///
/// There is no "create a person" here on purpose: accounts are made at sign-up,
/// with one password policy, and this only appoints somebody who already has
/// one.
class _PickPersonSheet extends ConsumerStatefulWidget {
  final String staffRole;
  final Set<String> alreadyOn;

  const _PickPersonSheet({required this.staffRole, required this.alreadyOn});

  @override
  ConsumerState<_PickPersonSheet> createState() => _PickPersonSheetState();
}

class _PickPersonSheetState extends ConsumerState<_PickPersonSheet> {
  final _query = TextEditingController();

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  List<PublicUser> _matching(List<PublicUser> all) {
    final q = _query.text.trim().toLowerCase();
    return [
      for (final u in all)
        if (!widget.alreadyOn.contains(u.id) &&
            (q.isEmpty ||
                u.fullName.toLowerCase().contains(q) ||
                u.username.toLowerCase().contains(q) ||
                u.mobileNo.contains(q) ||
                u.userCode.toLowerCase().contains(q)))
          u,
    ];
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(directoryUsersProvider);
    final all = async.valueOrNull;
    final label = TournamentStaff.label(widget.staffRole).toLowerCase();

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.8,
      builder: (context, controller) => Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('Add $label', style: context.texts.titleMedium),
                const SizedBox(height: 4),
                Text(
                  'Somebody with no role yet is promoted on the way in. '
                  'Anybody who already holds a different role is refused, and '
                  'the server says why.',
                  style: context.texts.bodySmall,
                ),
                const SizedBox(height: 12),
                SearchField(
                  controller: _query,
                  hint: 'Search by name, @username or mobile',
                  onChanged: (_) => setState(() {}),
                ),
              ],
            ),
          ),
          Expanded(
            child: Builder(
              builder: (context) {
                if (all == null && async.hasError) {
                  return ErrorState(
                    error: async.error!,
                    onRetry: () => ref.invalidate(directoryUsersProvider),
                  );
                }
                if (all == null) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: ListSkeleton(rows: 4),
                  );
                }
                final matches = _matching(all);
                if (matches.isEmpty) {
                  return const EmptyState(
                    icon: Icons.person_search_outlined,
                    title: 'Nobody matches',
                    message: 'Everyone found is already on this competition, '
                        'or the search is too narrow.',
                  );
                }
                return ListView.builder(
                  controller: controller,
                  itemCount: matches.length,
                  itemBuilder: (context, i) {
                    final u = matches[i];
                    return ListTile(
                      leading: CnAvatar(
                        name: u.fullName.isEmpty ? u.username : u.fullName,
                        size: 36,
                        imageUrl:
                            u.hasPhoto ? ApiConfig.userPhoto(u.id) : null,
                      ),
                      title: Text(
                        u.fullName.isEmpty ? u.username : u.fullName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text(
                        '@${u.username} · ${Roles.label(u.role)}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      onTap: () => Navigator.pop(context, u),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// The flattened roster of one competition, grouped by the team each player
/// is registered to.
class TournamentPlayersScreen extends ConsumerWidget {
  final String tournamentId;

  const TournamentPlayersScreen({super.key, required this.tournamentId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(tournamentPlayersProvider(tournamentId));
    final players = async.valueOrNull;

    return Scaffold(
      appBar: _CompetitionAppBar(tournamentId: tournamentId, title: 'Players'),
      body: players == null && async.hasError
          ? ErrorState(
              error: async.error!,
              onRetry: () =>
                  ref.invalidate(tournamentPlayersProvider(tournamentId)),
            )
          : RefreshIndicator(
              onRefresh: () async =>
                  ref.invalidate(tournamentPlayersProvider(tournamentId)),
              child: players == null
                  ? const Padding(
                      padding: EdgeInsets.all(16),
                      child: ListSkeleton(rows: 4),
                    )
                  : _PlayersByTeam(players: players),
            ),
    );
  }
}

class _PlayersByTeam extends StatelessWidget {
  final List<TournamentPlayer> players;

  const _PlayersByTeam({required this.players});

  @override
  Widget build(BuildContext context) {
    if (players.isEmpty) {
      return ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: const [
          EmptyState(
            icon: Icons.groups_outlined,
            title: 'Nobody registered yet',
            message: 'Players appear here once they are registered to a team '
                'in this competition.',
          ),
        ],
      );
    }

    // Keep the server's order rather than sorting by name: teams come back in
    // the order they were entered, and that is the order the organizer's own
    // paperwork is in.
    final byTeam = <String, ({String name, List<TournamentPlayer> players})>{};
    for (final p in players) {
      final group = byTeam[p.teamId];
      if (group == null) {
        byTeam[p.teamId] = (name: p.teamName, players: [p]);
      } else {
        group.players.add(p);
      }
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
      children: [
        SectionHeader(
          title: '${players.length} registered',
          subtitle: 'Across ${byTeam.length} '
              '${byTeam.length == 1 ? 'team' : 'teams'}',
        ),
        for (final group in byTeam.values)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: CnCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          group.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: context.texts.titleSmall,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${group.players.length}',
                        style: context.texts.labelLarge,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  for (final entry in group.players)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          CnAvatar(
                            name: entry.player.name,
                            size: 30,
                            imageUrl: entry.player.hasPhoto
                                ? ApiConfig.playerPhoto(entry.player.id)
                                : null,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              entry.player.name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: context.texts.bodyMedium,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            entry.player.code,
                            style: context.texts.labelSmall
                                ?.copyWith(color: context.cric.faint),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

/// A shared app bar that names the competition once it is known.
///
/// The name is read with `.valueOrNull`: a competition that fails to load
/// leaves the title as "Staff" and keeps the back arrow, instead of throwing
/// out of the app bar and taking the way out with it.
class _CompetitionAppBar extends ConsumerWidget implements PreferredSizeWidget {
  final String tournamentId;
  final String title;

  const _CompetitionAppBar({required this.tournamentId, required this.title});

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final name = ref.watch(tournamentProvider(tournamentId)).valueOrNull?.name;

    return AppBar(
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(title),
          if (name != null && name.isNotEmpty)
            Text(
              name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: context.texts.labelSmall?.copyWith(
                color: context.cric.muted,
              ),
            ),
        ],
      ),
    );
  }
}
