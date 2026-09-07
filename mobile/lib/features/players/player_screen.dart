import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_config.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/roster.dart';
import '../../core/models/social.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/common.dart';
import '../social/follow_button.dart';
import 'player_providers.dart';
import 'players_list_screen.dart';

/// A player's career: batting, bowling, fielding, form, insights and splits.
class PlayerScreen extends ConsumerWidget {
  final String playerId;

  const PlayerScreen({super.key, required this.playerId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(playerStatsProvider(playerId));
    final auth = ref.watch(authControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(async.valueOrNull?.player.name ?? 'Player'),
        actions: [
          if (auth.can(Caps.createTeam) && async.valueOrNull != null)
            IconButton(
              icon: const Icon(Icons.edit_outlined, size: 20),
              tooltip: 'Edit',
              onPressed: () async {
                final updated = await showModalBottomSheet<Player>(
                  context: context,
                  isScrollControlled: true,
                  builder: (context) =>
                      PlayerFormSheet(existing: async.valueOrNull!.player),
                );
                if (updated == null) return;
                ref.invalidate(playerStatsProvider(playerId));
                ref.invalidate(playersProvider);
              },
            ),
        ],
      ),
      body: async.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(16),
          child: ListSkeleton(rows: 4),
        ),
        error: (e, _) => ErrorState(
          error: e,
          onRetry: () => ref.invalidate(playerStatsProvider(playerId)),
        ),
        data: (stats) => RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(playerStatsProvider(playerId));
            ref.invalidate(playerInsightsProvider(playerId));
            ref.invalidate(playerSplitsProvider(playerId));
            ref.invalidate(playerAwardsProvider(playerId));
          },
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              _Header(player: stats.player),
              const SizedBox(height: 14),
              _ClaimCard(player: stats.player),
              const SizedBox(height: 4),
              _CareerLink(playerId: playerId, stats: stats),
              _AwardsList(playerId: playerId),
              if (stats.batting.hasPlayed) ...[
                const SectionHeader(title: 'Batting'),
                CnCard(
                  child: StatGrid(
                    columns: 4,
                    stats: [
                      (label: 'Mat', value: '${stats.batting.matches}'),
                      (label: 'Inns', value: '${stats.batting.innings}'),
                      (label: 'Runs', value: '${stats.batting.runs}'),
                      (label: 'HS', value: '${stats.batting.highest}'),
                      (label: 'Avg', value: Fmt.rate(stats.batting.average)),
                      (
                        label: 'SR',
                        value: stats.batting.strikeRate.toStringAsFixed(1)
                      ),
                      (label: 'NO', value: '${stats.batting.notOuts}'),
                      (label: 'Balls', value: '${stats.batting.balls}'),
                      (label: '4s', value: '${stats.batting.fours}'),
                      (label: '6s', value: '${stats.batting.sixes}'),
                      (label: '50s', value: '${stats.batting.fifties}'),
                      (label: '100s', value: '${stats.batting.hundreds}'),
                    ],
                  ),
                ),
              ],
              if (stats.bowling.hasBowled) ...[
                const SectionHeader(title: 'Bowling'),
                CnCard(
                  child: StatGrid(
                    columns: 4,
                    stats: [
                      (label: 'Mat', value: '${stats.bowling.matches}'),
                      (label: 'Inns', value: '${stats.bowling.innings}'),
                      (label: 'Overs', value: stats.bowling.overs),
                      (label: 'Wkts', value: '${stats.bowling.wickets}'),
                      (label: 'Runs', value: '${stats.bowling.runs}'),
                      (
                        label: 'Econ',
                        value: stats.bowling.economy.toStringAsFixed(2)
                      ),
                      (label: 'Avg', value: Fmt.rate(stats.bowling.average)),
                      (label: 'SR', value: Fmt.rate(stats.bowling.strikeRate)),
                      (label: 'Best', value: stats.bowling.best),
                      (label: 'Mdns', value: '${stats.bowling.maidens}'),
                    ],
                  ),
                ),
              ],
              const SectionHeader(title: 'Fielding'),
              CnCard(
                child: StatGrid(
                  // Four across, not five: at 375px the fifth column left no
                  // room for "RUN-OUTS" to survive.
                  columns: 4,
                  stats: [
                    (label: 'Catches', value: '${stats.fielding.catches}'),
                    (label: 'Run-outs', value: '${stats.fielding.runOuts}'),
                    (label: 'Stumps', value: '${stats.fielding.stumpings}'),
                    (label: 'Drops', value: '${stats.fielding.drops}'),
                    (label: 'Saved', value: '${stats.fielding.runsSaved}'),
                  ],
                ),
              ),
              if (stats.recent.isNotEmpty) ...[
                const SectionHeader(title: 'Recent form'),
                CnCard(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                  child: Column(
                    children: [
                      for (final f in stats.recent)
                        InkWell(
                          onTap: () => context.push(Routes.match(f.matchId)),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 9),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    f.teams,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: context.texts.bodySmall,
                                  ),
                                ),
                                if (f.bat != null) ...[
                                  CnBadge(text: f.bat!),
                                  const SizedBox(width: 6),
                                ],
                                if (f.bowl != null)
                                  CnBadge(
                                    text: f.bowl!,
                                    color: context.cric.four,
                                  ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
              _InsightsSection(playerId: playerId),
              _SplitsSection(playerId: playerId),
            ],
          ),
        ),
      ),
    );
  }
}

/// The way into the full career record.
class _CareerLink extends StatelessWidget {
  final String playerId;
  final PlayerStats stats;

  const _CareerLink({required this.playerId, required this.stats});

  @override
  Widget build(BuildContext context) {
    final played = stats.batting.matches;
    return CnCard(
      onTap: () => context.push(Routes.career(playerId)),
      child: Row(
        children: [
          Icon(Icons.history, size: 21, color: context.scheme.primary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Career history', style: context.texts.titleSmall),
                Text(
                  played == 0
                      ? 'Every match, once they have played one'
                      : 'All $played ${played == 1 ? 'match' : 'matches'}, '
                          'cup by cup',
                  style: context.texts.labelSmall,
                ),
              ],
            ),
          ),
          Icon(Icons.chevron_right, size: 20, color: context.cric.faint),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  final Player player;

  const _Header({required this.player});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        CnAvatar(
          name: player.name,
          size: 62,
          imageUrl: player.hasPhoto ? ApiConfig.playerPhoto(player.id) : null,
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(player.name, style: context.texts.headlineSmall),
              const SizedBox(height: 2),
              Text(player.styleLine, style: context.texts.bodySmall),
              if (player.code.isNotEmpty)
                Text(
                  player.code,
                  style: context.texts.labelSmall
                      ?.copyWith(color: context.cric.faint),
                ),
            ],
          ),
        ),
        FollowButton(
          entityType: FollowEntities.player,
          entityId: player.id,
        ),
      ],
    );
  }
}

/// Claim a roster profile whose phone number matches your account.
class _ClaimCard extends ConsumerWidget {
  final Player player;

  const _ClaimCard({required this.player});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    if (user == null) return const SizedBox.shrink();

    if (player.claimedBy == user.id) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: CnCard(
          color: context.cric.accentSoft,
          borderColor: context.scheme.primary.withValues(alpha: 0.25),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Row(
            children: [
              Icon(Icons.verified, size: 17, color: context.scheme.primary),
              const SizedBox(width: 10),
              Text('This is your profile', style: context.texts.bodySmall),
            ],
          ),
        ),
      );
    }

    // Only offer the claim when the server would actually accept it.
    final canClaim = !player.isClaimed &&
        user.isVerified &&
        player.phone != null &&
        player.phone == user.mobileNo;
    if (!canClaim) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: CnCard(
        child: Row(
          children: [
            Expanded(
              child: Text(
                'This profile matches your mobile number.',
                style: context.texts.bodySmall,
              ),
            ),
            ElevatedButton(
              onPressed: () async {
                try {
                  await ref.read(apiProvider).claimPlayer(player.id);
                  ref.invalidate(playerStatsProvider(player.id));
                  ref.invalidate(myPlayersProvider);
                  if (context.mounted) context.toast('Profile claimed');
                } catch (e) {
                  if (context.mounted) context.toastError(e);
                }
              },
              child: const Text('Claim'),
            ),
          ],
        ),
      ),
    );
  }
}

class _AwardsList extends ConsumerWidget {
  final String playerId;

  const _AwardsList({required this.playerId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final awards = ref.watch(playerAwardsProvider(playerId)).valueOrNull ?? const [];
    if (awards.isEmpty) return const SizedBox.shrink();

    return Column(
      children: [
        const SectionHeader(title: 'Honours'),
        CnCard(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
          child: Column(
            children: [
              for (final a in awards)
                InkWell(
                  onTap: () => context.push(Routes.match(a.matchId)),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 9),
                    child: Row(
                      children: [
                        Text(a.emoji, style: const TextStyle(fontSize: 16)),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(a.label, style: context.texts.bodySmall),
                        ),
                        if (a.detail.isNotEmpty)
                          Text(
                            a.detail,
                            style: context.texts.labelSmall
                                ?.copyWith(fontWeight: FontWeight.w700),
                          ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _InsightsSection extends ConsumerWidget {
  final String playerId;

  const _InsightsSection({required this.playerId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final insights = ref.watch(playerInsightsProvider(playerId)).valueOrNull;
    if (insights == null) return const SizedBox.shrink();

    final bat = insights.batting;
    final bowl = insights.bowling;
    if (bat.ballsFaced == 0 && bowl.ballsBowled == 0) {
      return const SizedBox.shrink();
    }

    return Column(
      children: [
        if (bat.ballsFaced > 0) ...[
          const SectionHeader(title: 'Batting insights'),
          CnCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                StatGrid(
                  columns: 4,
                  stats: [
                    (label: 'Dot %', value: Fmt.percent(bat.dotPct, places: 0)),
                    (
                      label: 'Bndry %',
                      value: Fmt.percent(bat.boundaryPct, places: 0)
                    ),
                    (label: 'In 4s/6s', value: '${bat.boundaryRuns}'),
                    (label: 'Balls', value: '${bat.ballsFaced}'),
                  ],
                ),
                if (bat.dismissals.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  Text('How out', style: context.texts.labelLarge),
                  const SizedBox(height: 8),
                  _BarBreakdown(
                    data: bat.dismissals,
                    labeller: (k) => k.replaceAll('_', ' '),
                    color: context.cric.wicket,
                  ),
                ],
                if (bat.shotsTracked > 0) ...[
                  const SizedBox(height: 16),
                  StatGrid(
                    columns: 3,
                    stats: [
                      (
                        label: 'Off side',
                        value: Fmt.percent(bat.offSidePct, places: 0)
                      ),
                      (
                        label: 'Leg side',
                        value: Fmt.percent(bat.legSidePct, places: 0)
                      ),
                      (label: 'Top area', value: bat.topZone),
                    ],
                  ),
                  if (bat.runsByZone.isNotEmpty) ...[
                    const SizedBox(height: 14),
                    Text('Runs by area', style: context.texts.labelLarge),
                    const SizedBox(height: 8),
                    _BarBreakdown(
                      data: bat.runsByZone,
                      labeller: (k) => k,
                      color: context.scheme.primary,
                    ),
                  ],
                ],
              ],
            ),
          ),
        ],
        if (bowl.ballsBowled > 0) ...[
          const SectionHeader(title: 'Bowling insights'),
          CnCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                StatGrid(
                  columns: 3,
                  stats: [
                    (label: 'Dot %', value: Fmt.percent(bowl.dotPct, places: 0)),
                    (label: 'Balls', value: '${bowl.ballsBowled}'),
                    (label: 'Tracked', value: '${bowl.pitchesTracked}'),
                  ],
                ),
                if (bowl.wicketsByType.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  Text('Wickets by type', style: context.texts.labelLarge),
                  const SizedBox(height: 8),
                  _BarBreakdown(
                    data: bowl.wicketsByType,
                    labeller: (k) => k.replaceAll('_', ' '),
                    color: context.cric.four,
                  ),
                ],
                if (bowl.lengthDist.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  Text('Lengths bowled', style: context.texts.labelLarge),
                  const SizedBox(height: 8),
                  _BarBreakdown(
                    data: bowl.lengthDist,
                    labeller: (k) => k,
                    color: context.cric.six,
                  ),
                ],
              ],
            ),
          ),
        ],
      ],
    );
  }
}

/// A horizontal bar per key, sized against the largest value.
class _BarBreakdown extends StatelessWidget {
  final Map<String, int> data;
  final String Function(String) labeller;
  final Color color;

  const _BarBreakdown({
    required this.data,
    required this.labeller,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final entries = data.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final max = entries.isEmpty ? 1 : entries.first.value;

    return Column(
      children: [
        for (final e in entries)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              children: [
                SizedBox(
                  width: 110,
                  child: Text(
                    labeller(e.key),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.texts.labelSmall,
                  ),
                ),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(3),
                    child: LinearProgressIndicator(
                      value: max == 0 ? 0 : e.value / max,
                      minHeight: 7,
                      color: color,
                      backgroundColor: context.cric.surfaceVariant,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                SizedBox(
                  width: 30,
                  child: Text(
                    '${e.value}',
                    textAlign: TextAlign.right,
                    style: context.texts.labelSmall,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _SplitsSection extends ConsumerWidget {
  final String playerId;

  const _SplitsSection({required this.playerId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final splits = ref.watch(playerSplitsProvider(playerId)).valueOrNull;
    if (splits == null) return const SizedBox.shrink();

    Widget table(String title, List<FormatSplit> rows) {
      // One row is the whole career, which the cards above already show.
      if (rows.length < 2) return const SizedBox.shrink();
      return Column(
        children: [
          SectionHeader(title: title),
          CnCard(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            child: Column(
              children: [
                Row(
                  children: [
                    const Expanded(child: SizedBox()),
                    for (final h in ['M', 'Runs', 'Avg', 'SR', 'Wkt', 'Econ'])
                      SizedBox(
                        width: 44,
                        child: Text(
                          h,
                          textAlign: TextAlign.right,
                          style: context.texts.labelSmall?.copyWith(
                            color: context.cric.faint,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 6),
                for (final r in rows)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 5),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(r.label,
                              style: context.texts.bodySmall),
                        ),
                        _cell(context, '${r.matches}'),
                        _cell(context, '${r.batting.runs}'),
                        _cell(context, Fmt.rate(r.batting.average)),
                        _cell(context,
                            r.batting.strikeRate.toStringAsFixed(0)),
                        _cell(context, '${r.bowling.wickets}'),
                        _cell(context,
                            r.bowling.economy.toStringAsFixed(1)),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
      );
    }

    return Column(
      children: [
        table('By format', splits.byFormat),
        table('By ball type', splits.byBall),
        if (splits.hasMatchup) ...[
          const SectionHeader(title: 'Batting matchups'),
          Row(
            children: [
              Expanded(child: _VsCard(vs: splits.vsPace)),
              const SizedBox(width: 10),
              Expanded(child: _VsCard(vs: splits.vsSpin)),
            ],
          ),
        ],
      ],
    );
  }

  static Widget _cell(BuildContext context, String value) => SizedBox(
        width: 44,
        child: Text(
          value,
          textAlign: TextAlign.right,
          style: context.texts.bodySmall?.copyWith(
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
      );
}

class _VsCard extends StatelessWidget {
  final BattingVsType vs;

  const _VsCard({required this.vs});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(vs.label, style: context.texts.titleSmall),
          const SizedBox(height: 12),
          StatGrid(
            columns: 2,
            stats: [
              (label: 'Runs', value: '${vs.runs}'),
              (label: 'Balls', value: '${vs.balls}'),
              (label: 'SR', value: vs.strikeRate.toStringAsFixed(0)),
              (label: 'Avg', value: Fmt.rate(vs.average)),
              (label: 'Dot %', value: Fmt.percent(vs.dotPct, places: 0)),
              (label: '4s/6s', value: '${vs.fours}/${vs.sixes}'),
            ],
          ),
        ],
      ),
    );
  }
}
