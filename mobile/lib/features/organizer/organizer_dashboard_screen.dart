import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_config.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/tournament.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'organizer_providers.dart';

/// An organizer's desk: the competitions, and the way into each one's staff
/// and roster.
///
/// The capability check below decides what to *draw*, never what is allowed.
/// `tournament.create` says this account may run competitions; it says nothing
/// about whose. Every write behind these cards is checked again by the server
/// against who owns that particular competition, so a second organizer holding
/// exactly the same capability is still refused. Hiding a control here only
/// saves somebody a tap that would end in a 403.
class OrganizerDashboardScreen extends ConsumerWidget {
  const OrganizerDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Organizer')),
      // The gate renders inside the Scaffold so the back arrow survives it,
      // the same reason the error states below do.
      body: auth.can(Caps.createTournament)
          ? _Desk(user: auth.user)
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              children: [
                GateCard(
                  what: 'organize competitions',
                  signedIn: auth.isSignedIn,
                  role: auth.user?.role,
                  onSignIn: () => context.push(Routes.login),
                  onRegister: () => context.push(Routes.register),
                ),
              ],
            ),
    );
  }
}

class _Desk extends ConsumerWidget {
  final AppUser? user;

  const _Desk({required this.user});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(organizerTournamentsProvider);
    // `.valueOrNull`, never `.value`: `.value` rethrows when the provider
    // failed, and a throw from this build would take the whole Scaffold —
    // back arrow included — and replace it with a red box.
    final tournaments = async.valueOrNull;

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(organizerTournamentsProvider);
        ref.invalidate(myOrganizerProvider);
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          _OrganizerHeader(user: user),
          const SectionHeader(
            title: 'Your competitions',
            subtitle: 'Staff and players are yours to run on the competitions '
                'you own. The server checks ownership on every change.',
          ),
          if (tournaments == null && async.hasError)
            ErrorState(
              error: async.error!,
              onRetry: () => ref.invalidate(organizerTournamentsProvider),
            )
          else if (tournaments == null)
            const ListSkeleton(rows: 3)
          else if (tournaments.isEmpty)
            EmptyState(
              icon: Icons.emoji_events_outlined,
              title: 'No competitions yet',
              message: 'Competitions you run show up here, with their umpires, '
                  'commentators and registered players.',
              actionLabel: 'Browse tournaments',
              onAction: () => context.push(Routes.tournaments),
            )
          else
            for (final t in tournaments)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _CompetitionCard(tournament: t),
              ),
        ],
      ),
    );
  }
}

/// Who is signed in, and where they organize — when the account has a posting.
class _OrganizerHeader extends ConsumerWidget {
  final AppUser? user;

  const _OrganizerHeader({required this.user});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final account = user;
    if (account == null) return const SizedBox.shrink();

    // A missing posting is normal — only the admin roster carries it — so this
    // reads whatever came back and shows the role when nothing did.
    final organizer = ref.watch(myOrganizerProvider).valueOrNull;
    final posting = organizer?.posting ?? '';

    return CnCard(
      child: Row(
        children: [
          CnAvatar(
            name: account.displayName,
            size: 46,
            imageUrl:
                account.hasPhoto ? ApiConfig.userPhoto(account.id) : null,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(account.displayName, style: context.texts.titleSmall),
                const SizedBox(height: 2),
                Text(
                  posting.isEmpty ? Roles.label(account.role) : posting,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.bodySmall,
                ),
                if (organizer != null && !organizer.isActive) ...[
                  const SizedBox(height: 6),
                  CnBadge(text: 'Suspended', color: context.cric.wicket),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// One competition, with its two working views.
class _CompetitionCard extends StatelessWidget {
  final TournamentSummary tournament;

  const _CompetitionCard({required this.tournament});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      onTap: () => context.push(Routes.tournament(tournament.id)),
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
                      tournament.name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: context.texts.titleSmall,
                    ),
                    const SizedBox(height: 2),
                    Text(tournament.subtitle, style: context.texts.bodySmall),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, size: 20, color: context.cric.faint),
            ],
          ),
          const SizedBox(height: 12),
          // Two buttons, not four: at 375px a row of narrow labelled controls
          // truncates into nonsense, so the pair each get half the width.
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () =>
                      context.push(Routes.tournamentStaff(tournament.id)),
                  icon: const Icon(Icons.badge_outlined, size: 17),
                  label: const Text('Staff'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () =>
                      context.push(Routes.tournamentPlayers(tournament.id)),
                  icon: const Icon(Icons.groups_outlined, size: 17),
                  label: const Text('Players'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
