import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/org.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'organizer_providers.dart';

/// The competitions an umpire or commentator was appointed to.
///
/// For those two roles this is the whole product: they hold no capabilities of
/// their own, and everything they are allowed to do comes from being on
/// somebody's staff. So this screen carries the competition, the job, whether
/// they are currently stood down, and the two working views they may read —
/// not a list of ids they have to decode.
class MyAssignmentsScreen extends ConsumerWidget {
  const MyAssignmentsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(myStaffingProvider);
    // `.valueOrNull`, never `.value`: `.value` rethrows on a failed provider,
    // and a throw in this build replaces the Scaffold — back arrow and all.
    final staffing = async.valueOrNull;
    final user = ref.watch(currentUserProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('My assignments')),
      // Rendered inside the Scaffold so a failure is still escapable.
      body: staffing == null && async.hasError
          ? ErrorState(
              error: async.error!,
              onRetry: () => ref.invalidate(myStaffingProvider),
            )
          : RefreshIndicator(
              onRefresh: () async => ref.invalidate(myStaffingProvider),
              child: staffing == null
                  ? const Padding(
                      padding: EdgeInsets.all(16),
                      child: ListSkeleton(rows: 3),
                    )
                  : _Assignments(staffing: staffing, user: user),
            ),
    );
  }
}

class _Assignments extends StatelessWidget {
  final List<MyStaffing> staffing;
  final AppUser? user;

  const _Assignments({required this.staffing, required this.user});

  @override
  Widget build(BuildContext context) {
    if (staffing.isEmpty) {
      return ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          EmptyState(
            icon: Icons.assignment_outlined,
            title: 'No competitions yet',
            message: 'An organizer adds you to their competition and it '
                'appears here, with the fixtures and the team sheets you are '
                'allowed to see.',
            actionLabel: 'Browse tournaments',
            onAction: () => context.push(Routes.tournaments),
          ),
        ],
      );
    }

    final groups = groupStaffing(staffing);
    final active = staffing.where((s) => s.isActive).length;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
      children: [
        _Summary(user: user, total: staffing.length, active: active),
        for (final group in groups) ...[
          SectionHeader(
            title: 'As ${TournamentStaff.label(group.role).toLowerCase()}',
            trailing: Text(
              '${group.entries.length}',
              style: context.texts.labelLarge,
            ),
          ),
          for (final entry in group.entries)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _AssignmentCard(staffing: entry),
            ),
        ],
      ],
    );
  }
}

class _Summary extends StatelessWidget {
  final AppUser? user;
  final int total;
  final int active;

  const _Summary({
    required this.user,
    required this.total,
    required this.active,
  });

  @override
  Widget build(BuildContext context) {
    final name = user?.firstName ?? '';
    final line = active == total
        ? 'You are working $total ${total == 1 ? 'competition' : 'competitions'}.'
        : 'You are working $active of $total '
            '${total == 1 ? 'competition' : 'competitions'} — the rest have '
            'stood you down for now.';

    return CnCard(
      child: Row(
        children: [
          CnAvatar(name: user?.displayName ?? 'You', size: 44),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name.isEmpty ? 'Your assignments' : 'Hello, $name',
                  style: context.texts.titleSmall,
                ),
                const SizedBox(height: 2),
                Text(line, style: context.texts.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// One competition somebody works, and the ways into it.
class _AssignmentCard extends StatelessWidget {
  final MyStaffing staffing;

  const _AssignmentCard({required this.staffing});

  @override
  Widget build(BuildContext context) {
    final name = staffing.tournamentName.isEmpty
        ? 'Competition ${staffing.tournamentId}'
        : staffing.tournamentName;

    return CnCard(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      onTap: () => context.push(Routes.tournament(staffing.tournamentId)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: context.texts.titleSmall,
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        CnBadge(
                          text: TournamentStaff.label(staffing.staffRole),
                        ),
                        if (!staffing.isActive) ...[
                          const SizedBox(width: 6),
                          CnBadge(
                            text: 'Stood down',
                            color: context.cric.amber,
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, size: 20, color: context.cric.faint),
            ],
          ),
          if (!staffing.isActive) ...[
            const SizedBox(height: 8),
            Text(
              'The organizer has stood you down for this competition. You can '
              'still read it; ask them to bring you back before the next game.',
              style: context.texts.bodySmall,
            ),
          ],
          const SizedBox(height: 12),
          // Two halves rather than a row of narrow controls, so both labels
          // still read at 375px.
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => context
                      .push(Routes.tournamentPlayers(staffing.tournamentId)),
                  icon: const Icon(Icons.groups_outlined, size: 17),
                  label: const Text('Team sheet'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => context
                      .push(Routes.tournamentStaff(staffing.tournamentId)),
                  icon: const Icon(Icons.badge_outlined, size: 17),
                  label: const Text('Staff'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
