import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/match.dart';
import '../../core/models/social.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/common.dart';
import '../leaderboards/leaderboard_providers.dart';
import '../matches/match_providers.dart';
import '../notifications/notification_providers.dart';
import '../players/player_providers.dart';
import '../teams/team_providers.dart';
import '../tournaments/tournament_providers.dart';

/// The landing screen: what is live now, what you can act on, and the way in
/// to everything else.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final live = ref.watch(liveMatchesProvider);
    final matches = ref.watch(matchesListProvider);
    final unread = ref.watch(unreadNotificationsProvider).valueOrNull ?? 0;

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: Row(
          children: [
            Icon(Icons.sports_cricket,
                size: 21, color: context.scheme.primary),
            const SizedBox(width: 8),
            RichText(
              text: TextSpan(
                style: context.texts.titleLarge?.copyWith(fontSize: 19),
                children: [
                  const TextSpan(text: 'Cric'),
                  TextSpan(
                    text: 'Netra',
                    style: TextStyle(color: context.scheme.primary),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.search, size: 22),
            tooltip: 'Search',
            onPressed: () => context.push(Routes.search),
          ),
          _BellButton(unread: unread),
          IconButton(
            tooltip: user == null ? 'Sign in' : 'Account',
            onPressed: () => context.push(
              user == null ? Routes.login : Routes.account,
            ),
            icon: user == null
                ? const Icon(Icons.person_outline, size: 22)
                : CnAvatar(name: user.displayName, size: 26),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(liveMatchesProvider);
          ref.invalidate(matchesListProvider);
          ref.invalidate(leaderboardsProvider);
          ref.invalidate(pendingOfficialsProvider);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            _Greeting(user: user),
            const SizedBox(height: 16),

            live.when(
              loading: () => const SkeletonBox(height: 150, radius: 16),
              error: (_, _) => const SizedBox.shrink(),
              data: (states) => states.isEmpty
                  ? const _WelcomeHero()
                  : _LiveSection(matches: states),
            ),

            const _OfficiatingRequests(),

            const SizedBox(height: 20),
            const _CountsStrip(),

            SectionHeader(
              title: 'Recent matches',
              trailing: TextButton(
                onPressed: () => context.go(Routes.matches),
                child: const Text('See all'),
              ),
            ),
            matches.when(
              loading: () => const ListSkeleton(rows: 3),
              error: (e, _) => ErrorState(
                error: e,
                onRetry: () => ref.invalidate(matchesListProvider),
              ),
              data: (list) {
                if (list.isEmpty) {
                  return EmptyState(
                    icon: Icons.sports_cricket_outlined,
                    title: 'No matches yet',
                    message: ref.watch(authControllerProvider).can(Caps.createMatch)
                        ? 'Tap the plus button to start scoring.'
                        : 'Live and finished matches appear here.',
                  );
                }
                final recent = list.reversed.take(5).toList();
                return Column(
                  children: [
                    for (final m in recent)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: MatchRowCard(match: m),
                      ),
                  ],
                );
              },
            ),

            const _TopRunScorers(),

            const SectionHeader(title: 'Explore'),
            const _QuickActions(),
          ],
        ),
      ),
    );
  }
}

class _Greeting extends StatelessWidget {
  final AppUser? user;

  const _Greeting({required this.user});

  @override
  Widget build(BuildContext context) {
    // Signed out there is no name, and "Good afternoon, there" reads like a
    // template nobody filled in.
    final name = user?.firstName;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          Fmt.longDate(DateTime.now()),
          style: context.texts.labelSmall?.copyWith(
            color: context.cric.faint,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          [Fmt.greeting(), ?name].join(', '),
          style: context.texts.headlineSmall,
        ),
      ],
    );
  }
}

class _BellButton extends StatelessWidget {
  final int unread;

  const _BellButton({required this.unread});

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: [
        IconButton(
          icon: const Icon(Icons.notifications_none, size: 22),
          tooltip: 'Notifications',
          onPressed: () => context.push(Routes.notifications),
        ),
        if (unread > 0)
          Positioned(
            top: 8,
            right: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
              constraints: const BoxConstraints(minWidth: 15),
              decoration: BoxDecoration(
                color: context.cric.wicket,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                unread > 99 ? '99+' : '$unread',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _WelcomeHero extends ConsumerWidget {
  const _WelcomeHero();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final canScore = ref.watch(authControllerProvider).can(Caps.createMatch);

    return CnCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const CnBadge(text: 'Nothing live right now'),
          const SizedBox(height: 12),
          Text('Score your cricket, by your rules',
              style: context.texts.titleLarge),
          const SizedBox(height: 8),
          Text(
            'Ball-by-ball scoring with a rulebook you configure: box, gully, '
            'T20 or your own. Career stats build themselves.',
            style: context.texts.bodySmall,
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              if (canScore) ...[
                ElevatedButton.icon(
                  onPressed: () => context.push(Routes.newMatch),
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Start a match'),
                ),
                const SizedBox(width: 10),
              ],
              OutlinedButton(
                onPressed: () => context.push(
                  canScore ? Routes.rules : Routes.login,
                ),
                child: Text(canScore ? 'Custom rules' : 'Sign in to score'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// A carousel of the matches happening right now.
class _LiveSection extends StatefulWidget {
  final List<MatchState> matches;

  const _LiveSection({required this.matches});

  @override
  State<_LiveSection> createState() => _LiveSectionState();
}

class _LiveSectionState extends State<_LiveSection> {
  late final PageController _pages = PageController(viewportFraction: 0.94);
  int _index = 0;

  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const LiveDot(),
            const SizedBox(width: 6),
            Text(
              'Live now · ${widget.matches.length}',
              style: context.texts.labelLarge?.copyWith(
                fontWeight: FontWeight.w700,
                color: context.cric.wicket,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        SizedBox(
          height: 178,
          child: PageView.builder(
            controller: _pages,
            itemCount: widget.matches.length,
            onPageChanged: (i) => setState(() => _index = i),
            itemBuilder: (context, i) => Padding(
              padding: EdgeInsets.only(
                right: i == widget.matches.length - 1 ? 0 : 8,
              ),
              child: LiveMatchCard(match: widget.matches[i]),
            ),
          ),
        ),
        if (widget.matches.length > 1) ...[
          const SizedBox(height: 10),
          Center(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (var i = 0; i < widget.matches.length; i++)
                  Container(
                    width: i == _index ? 16 : 6,
                    height: 6,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                      color: i == _index
                          ? context.scheme.primary
                          : context.cric.line,
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

/// A live match with its score and a win-probability read.
class LiveMatchCard extends StatelessWidget {
  final MatchState match;

  const LiveMatchCard({super.key, required this.match});

  /// A rough read on who is winning, from the run rate and wickets in hand.
  /// Deliberately simple — it is a talking point, not a prediction model.
  static double? winProbability(Innings innings) {
    if (innings.isComplete) return null;
    final wicketsLeft = innings.wicketsLeft;
    if (innings.isChase) {
      final required = innings.requiredRuns ?? 0;
      if (required <= 0) return 100;
      final rrr = innings.requiredRunRate ?? 0;
      final p = 50 + (8 - rrr) * 5 + (wicketsLeft - 5) * 4;
      return p.clamp(4, 96);
    }
    final p = 50 + (innings.runRate - 7.5) * 3 + (wicketsLeft - 5) * 3;
    return p.clamp(28, 72);
  }

  @override
  Widget build(BuildContext context) {
    final innings = match.current;
    if (innings == null) return const SizedBox.shrink();
    final prob = winProbability(innings);

    return CnCard(
      onTap: () => context.push(Routes.match(match.id)),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const LiveDot(size: 7),
              const SizedBox(width: 6),
              Text(
                match.rulesName,
                style: context.texts.labelSmall?.copyWith(
                  color: context.cric.faint,
                  letterSpacing: 0.4,
                ),
              ),
              const Spacer(),
              Icon(Icons.chevron_right, size: 17, color: context.cric.faint),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            match.title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: context.texts.titleSmall,
          ),
          const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                innings.scoreLine,
                style: context.texts.headlineMedium?.copyWith(
                  height: 1,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
              const SizedBox(width: 10),
              Text(
                '${innings.oversStr} ov · CRR ${innings.runRate.toStringAsFixed(2)}',
                style: context.texts.bodySmall,
              ),
            ],
          ),
          if (innings.isChase && innings.requiredRuns != null) ...[
            const SizedBox(height: 6),
            Text(
              'Need ${innings.requiredRuns} off ${innings.ballsRemaining} balls',
              style: context.texts.bodySmall
                  ?.copyWith(color: context.scheme.primary),
            ),
          ],
          const Spacer(),
          if (prob != null) ...[
            Row(
              children: [
                Text(
                  'WIN PROBABILITY',
                  style: context.texts.labelSmall?.copyWith(
                    color: context.cric.faint,
                    fontSize: 9,
                    letterSpacing: 0.6,
                  ),
                ),
                const Spacer(),
                Text(
                  '${prob.round()}%',
                  style: context.texts.labelSmall
                      ?.copyWith(fontWeight: FontWeight.w700),
                ),
              ],
            ),
            const SizedBox(height: 5),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: prob / 100,
                minHeight: 5,
                backgroundColor: context.cric.surfaceVariant,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// A compact row for a match in a list.
class MatchRowCard extends StatelessWidget {
  final MatchSummary match;

  const MatchRowCard({super.key, required this.match});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      onTap: () => context.push(Routes.match(match.id)),
      child: Row(
        children: [
          CnAvatar(name: match.teamA, size: 38),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  match.title,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 2),
                Text(
                  match.subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          match.isLive
              ? CnBadge(text: 'LIVE', color: context.cric.wicket)
              : CnBadge(text: 'Result', color: context.cric.muted),
        ],
      ),
    );
  }
}

/// Umpires asking to officiate matches you manage.
class _OfficiatingRequests extends ConsumerWidget {
  const _OfficiatingRequests();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requests = ref.watch(pendingOfficialsProvider).valueOrNull ?? const [];
    if (requests.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: CnCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Requests to officiate · ${requests.length}',
              style: context.texts.titleSmall,
            ),
            const SizedBox(height: 10),
            for (final r in requests)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 5),
                child: Row(
                  children: [
                    CnAvatar(name: r.umpireName, size: 30),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(r.umpireName,
                              style: context.texts.bodyMedium),
                          Text(r.matchLabel,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: context.texts.labelSmall),
                        ],
                      ),
                    ),
                    TextButton(
                      onPressed: () async {
                        try {
                          await ref
                              .read(apiProvider)
                              .approveOfficial(r.matchId, r.umpireId);
                          ref.invalidate(pendingOfficialsProvider);
                          if (context.mounted) context.toast('Approved');
                        } catch (e) {
                          if (context.mounted) context.toastError(e);
                        }
                      },
                      child: const Text('Approve'),
                    ),
                    IconButton(
                      iconSize: 17,
                      icon: const Icon(Icons.close),
                      onPressed: () async {
                        try {
                          await ref
                              .read(apiProvider)
                              .removeOfficial(r.matchId, r.umpireId);
                          ref.invalidate(pendingOfficialsProvider);
                        } catch (e) {
                          if (context.mounted) context.toastError(e);
                        }
                      },
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Matches, players, teams and tournaments at a glance.
class _CountsStrip extends ConsumerWidget {
  const _CountsStrip();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final matches = ref.watch(matchesListProvider).valueOrNull;
    final players = ref.watch(playersProvider).valueOrNull;
    final teams = ref.watch(teamsProvider).valueOrNull;
    final tournaments = ref.watch(tournamentsProvider).valueOrNull;

    // A count that has not arrived is unknown, not zero. Showing "TEAMS 0" for
    // several seconds and then flipping to 2 reads as a bug, and a reader who
    // glances away has been told something false.
    String count(List<Object?>? list) => list == null ? '—' : '${list.length}';
    final liveCount = matches?.where((m) => m.isLive).length;

    return CnCard(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: [
          Expanded(
            child: StatTile(label: 'Matches', value: count(matches)),
          ),
          Expanded(
            child: StatTile(
              label: 'Live now',
              value: liveCount == null ? '—' : '$liveCount',
              valueColor: (liveCount ?? 0) > 0 ? context.cric.wicket : null,
            ),
          ),
          Expanded(
            child: StatTile(label: 'Players', value: count(players)),
          ),
          Expanded(
            child: StatTile(label: 'Teams', value: count(teams)),
          ),
          Expanded(
            child: StatTile(
              label: 'Cups',
              value: count(tournaments),
            ),
          ),
        ],
      ),
    );
  }
}

class _TopRunScorers extends ConsumerWidget {
  const _TopRunScorers();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final boards = ref.watch(leaderboardsProvider).valueOrNull;
    LeaderboardBoard? runs;
    for (final b in boards?.boards ?? const <LeaderboardBoard>[]) {
      if (b.key == 'most_runs') runs = b;
    }
    if (runs == null || runs.entries.isEmpty) return const SizedBox.shrink();

    return Column(
      children: [
        SectionHeader(
          title: 'Top run scorers',
          trailing: TextButton(
            onPressed: () => context.push(Routes.leaderboards),
            child: const Text('All boards'),
          ),
        ),
        CnCard(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
          child: Column(
            children: [
              for (var i = 0; i < runs.entries.take(5).length; i++)
                LeaderboardRow(
                  rank: i + 1,
                  entry: runs.entries[i],
                ),
            ],
          ),
        ),
      ],
    );
  }
}

/// One row of a leaderboard, shared by home and the boards screen.
class LeaderboardRow extends StatelessWidget {
  final int rank;
  final LeaderboardEntry entry;

  const LeaderboardRow({super.key, required this.rank, required this.entry});

  @override
  Widget build(BuildContext context) {
    final medal = _medal(rank);

    return InkWell(
      onTap: () => context.push(Routes.player(entry.playerId)),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 9),
        child: Row(
          children: [
            Container(
              width: 24,
              height: 24,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: medal?.withValues(alpha: 0.16) ??
                    context.cric.surfaceVariant,
                borderRadius: BorderRadius.circular(7),
              ),
              child: Text(
                '$rank',
                style: context.texts.labelSmall?.copyWith(
                  color: medal ?? context.cric.faint,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                entry.name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: context.texts.bodyMedium,
              ),
            ),
            if (entry.detail != null && entry.detail!.isNotEmpty) ...[
              Text(entry.detail!, style: context.texts.labelSmall),
              const SizedBox(width: 12),
            ],
            Text(
              entry.valueText,
              style: context.texts.bodyMedium?.copyWith(
                fontWeight: FontWeight.w700,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ],
        ),
      ),
    );
  }

  static Color? _medal(int rank) => switch (rank) {
        1 => const Color(0xFFF5B301),
        2 => const Color(0xFF9AA7B1),
        3 => const Color(0xFFCD8B50),
        _ => null,
      };
}

class _QuickActions extends StatelessWidget {
  const _QuickActions();

  static const _tiles = <({IconData icon, String label, String route})>[
    (icon: Icons.groups_outlined, label: 'Teams', route: Routes.teams),
    (icon: Icons.person_outline, label: 'Players', route: Routes.players),
    (icon: Icons.emoji_events_outlined, label: 'Cups', route: Routes.tournaments),
    (
      icon: Icons.leaderboard_outlined,
      label: 'Stats',
      route: Routes.leaderboards
    ),
    (icon: Icons.tune, label: 'Rules', route: Routes.rules),
    (icon: Icons.place_outlined, label: 'Venues', route: Routes.venues),
    (icon: Icons.play_circle_outline, label: 'Clips', route: Routes.highlights),
    (icon: Icons.calculate_outlined, label: 'Tools', route: Routes.tools),
  ];

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: _tiles.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 4,
        mainAxisSpacing: 10,
        crossAxisSpacing: 10,
        childAspectRatio: 0.92,
      ),
      itemBuilder: (context, i) {
        final t = _tiles[i];
        return CnCard(
          padding: const EdgeInsets.all(8),
          onTap: () => context.push(t.route),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(t.icon, size: 22, color: context.scheme.primary),
              const SizedBox(height: 6),
              Text(
                t.label,
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: context.texts.labelSmall?.copyWith(fontSize: 10.5),
              ),
            ],
          ),
        );
      },
    );
  }
}
