import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/models/career.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/common.dart';
import 'player_providers.dart';

/// A player's whole record: every match they have played, and how they went in
/// each competition.
///
/// The profile answers "how good are they". This answers "what have they
/// actually done" — the question a selector, a captain or the player
/// themselves is really asking.
class CareerScreen extends ConsumerStatefulWidget {
  final String playerId;

  const CareerScreen({super.key, required this.playerId});

  @override
  ConsumerState<CareerScreen> createState() => _CareerScreenState();
}

enum _Tab { overview, tournaments, matches }

class _CareerScreenState extends ConsumerState<CareerScreen> {
  _Tab _tab = _Tab.overview;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(playerHistoryProvider(widget.playerId));

    return Scaffold(
      appBar: AppBar(title: Text(async.valueOrNull?.player.name ?? 'Career')),
      body: async.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(16),
          child: ListSkeleton(rows: 4),
        ),
        error: (e, _) => ErrorState(
          error: e,
          onRetry: () =>
              ref.invalidate(playerHistoryProvider(widget.playerId)),
        ),
        data: (history) {
          if (!history.hasPlayed) {
            return EmptyState(
              icon: Icons.sports_cricket_outlined,
              title: '${history.player.name} has not played yet',
              message:
                  'Once they take the field, every match they play shows up '
                  'here with their batting, bowling and fielding.',
            );
          }
          return RefreshIndicator(
            // Await the refetch so the spinner stays up until the data lands.
            onRefresh: () =>
                ref.refresh(playerHistoryProvider(widget.playerId).future),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              children: [
                _CareerSummary(history: history),
                const SizedBox(height: 14),
                CnSegmented<_Tab>(
                  selected: _tab,
                  onChanged: (v) => setState(() => _tab = v),
                  options: const [
                    (value: _Tab.overview, label: 'Overview'),
                    (value: _Tab.tournaments, label: 'Cups'),
                    (value: _Tab.matches, label: 'Matches'),
                  ],
                ),
                const SizedBox(height: 6),
                switch (_tab) {
                  _Tab.overview => _Overview(history: history),
                  _Tab.tournaments => _Tournaments(history: history),
                  _Tab.matches => _Matches(history: history),
                },
              ],
            ),
          );
        },
      ),
    );
  }
}

// ---------------------------------------------------------------- summary

class _CareerSummary extends StatelessWidget {
  final PlayerHistory history;

  const _CareerSummary({required this.history});

  @override
  Widget build(BuildContext context) {
    final span = _span(history);

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              CnAvatar(name: history.player.name, size: 44),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(history.player.name, style: context.texts.titleSmall),
                    if (span != null)
                      Text(span, style: context.texts.labelSmall),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          StatGrid(
            columns: 4,
            stats: [
              (label: 'Mat', value: '${history.matchesPlayed}'),
              (label: 'Won', value: '${history.won}'),
              (label: 'Lost', value: '${history.lost}'),
              (label: 'Win %', value: Fmt.rate1(history.winPct)),
            ],
          ),
        ],
      ),
    );
  }

  /// "Since 12 Mar 2024 · 18 matches" — the career's span in one line.
  static String? _span(PlayerHistory h) {
    final debut = Fmt.dateTime(h.debut);
    if (debut.isEmpty) return null;
    final first = debut.split(',').first;
    final last = Fmt.dateTime(h.lastPlayed).split(',').first;
    if (h.matchesPlayed == 1 || first == last) return 'Played $first';
    return '$first — $last';
  }
}

// --------------------------------------------------------------- overview

class _Overview extends StatelessWidget {
  final PlayerHistory history;

  const _Overview({required this.history});

  @override
  Widget build(BuildContext context) {
    final best = history.bestInnings;
    final spell = history.bestSpell;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (best != null || spell != null) ...[
          const SectionHeader(title: 'Career best'),
          if (best != null && best.batted)
            _BestCard(
              icon: Icons.sports_cricket,
              title: '${best.runs}${best.notOut ? '*' : ''} (${best.balls})',
              subtitle: 'v ${best.opponent}',
              context: _matchContext(best),
              match: best,
            ),
          if (spell != null && spell.bowled && (spell.wickets ?? 0) > 0) ...[
            const SizedBox(height: 10),
            _BestCard(
              icon: Icons.sports_baseball_outlined,
              title: spell.bowlLine ?? '',
              subtitle: 'v ${spell.opponent}',
              context: _matchContext(spell),
              match: spell,
            ),
          ],
        ],
        if (history.batting.innings > 0) ...[
          const SectionHeader(title: 'Batting'),
          CnCard(
            child: StatGrid(
              columns: 4,
              stats: [
                (label: 'Inns', value: '${history.batting.innings}'),
                (label: 'Runs', value: Fmt.count(history.batting.runs)),
                (label: 'HS', value: '${history.batting.highest}'),
                (label: 'Avg', value: Fmt.rate(history.batting.average)),
                (label: 'SR', value: Fmt.rate(history.batting.strikeRate)),
                (label: '50s', value: '${history.batting.fifties}'),
                (label: '100s', value: '${history.batting.hundreds}'),
                (label: 'NO', value: '${history.batting.notOuts}'),
              ],
            ),
          ),
        ],
        if (history.bowling.balls > 0) ...[
          const SectionHeader(title: 'Bowling'),
          CnCard(
            child: StatGrid(
              columns: 4,
              stats: [
                (label: 'Inns', value: '${history.bowling.innings}'),
                (label: 'Overs', value: history.bowling.overs),
                (label: 'Wkts', value: '${history.bowling.wickets}'),
                (label: 'Best', value: history.bowling.best),
                (label: 'Avg', value: Fmt.rate(history.bowling.average)),
                (label: 'Econ', value: Fmt.rate(history.bowling.economy)),
                (label: 'Runs', value: '${history.bowling.runs}'),
                (label: 'Mdns', value: '${history.bowling.maidens}'),
              ],
            ),
          ),
        ],
        const SectionHeader(title: 'Fielding'),
        CnCard(
          child: StatGrid(
            columns: 4,
            stats: [
              (label: 'Catches', value: '${history.fielding.catches}'),
              (label: 'Run outs', value: '${history.fielding.runOuts}'),
              (label: 'Stumpings', value: '${history.fielding.stumpings}'),
              (label: 'Saved', value: '${history.fielding.runsSaved}'),
            ],
          ),
        ),
        if (history.byYear.length > 1) ...[
          const SectionHeader(title: 'Season by season'),
          for (final year in history.byYear)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _BucketCard(bucket: year),
            ),
        ],
        if (history.byTeam.isNotEmpty) ...[
          const SectionHeader(title: 'Teams played for'),
          for (final team in history.byTeam)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _BucketCard(bucket: team),
            ),
        ],
      ],
    );
  }

  static String _matchContext(CareerMatch m) {
    final date = Fmt.dateTime(m.playedOn).split(',').first;
    return [
      if (m.tournament != null) m.tournament!,
      if (date.isNotEmpty) date,
    ].join(' · ');
  }
}

class _BestCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final String context;
  final CareerMatch match;

  const _BestCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.context,
    required this.match,
  });

  @override
  Widget build(BuildContext ctx) {
    return CnCard(
      onTap: () => ctx.push(Routes.match(match.matchId)),
      child: Row(
        children: [
          Icon(icon, size: 22, color: ctx.scheme.primary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: ctx.texts.titleMedium),
                Text(subtitle, style: ctx.texts.bodySmall),
                if (context.isNotEmpty)
                  Text(context, style: ctx.texts.labelSmall),
              ],
            ),
          ),
          Icon(Icons.chevron_right, size: 20, color: ctx.cric.faint),
        ],
      ),
    );
  }
}

// ------------------------------------------------------------ tournaments

class _Tournaments extends StatelessWidget {
  final PlayerHistory history;

  const _Tournaments({required this.history});

  @override
  Widget build(BuildContext context) {
    if (history.byTournament.isEmpty) {
      return const Padding(
        padding: EdgeInsets.only(top: 24),
        child: EmptyState(
          icon: Icons.emoji_events_outlined,
          title: 'No tournament matches yet',
          message:
              'Matches played outside a competition still count towards the '
              'career record, but only cup games are broken down here.',
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final cup in history.byTournament)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: _BucketCard(bucket: cup, detailed: true),
          ),
      ],
    );
  }
}

/// One grouping's record — a tournament, a season or a side.
class _BucketCard extends StatelessWidget {
  final CareerBucket bucket;

  /// Show the full batting and bowling lines rather than a one-line summary.
  final bool detailed;

  const _BucketCard({required this.bucket, this.detailed = false});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(bucket.label, style: context.texts.titleSmall),
              ),
              CnBadge(
                text: '${bucket.matches} '
                    '${bucket.matches == 1 ? 'match' : 'matches'}',
              ),
            ],
          ),
          if (bucket.won + bucket.lost > 0) ...[
            const SizedBox(height: 4),
            Text(
              '${bucket.won} won · ${bucket.lost} lost',
              style: context.texts.labelSmall,
            ),
          ],
          const SizedBox(height: 12),
          if (!bucket.hasBatting && !bucket.hasBowling)
            Text(
              'Did not bat or bowl.',
              style: context.texts.bodySmall,
            ),
          if (bucket.hasBatting) ...[
            _MiniStats(
              label: 'Batting',
              stats: detailed
                  ? [
                      (label: 'Inns', value: '${bucket.batting.innings}'),
                      (label: 'Runs', value: '${bucket.batting.runs}'),
                      (label: 'HS', value: '${bucket.batting.highest}'),
                      (label: 'Avg', value: Fmt.rate(bucket.batting.average)),
                      (label: 'SR', value: Fmt.rate(bucket.batting.strikeRate)),
                      (label: '4s', value: '${bucket.batting.fours}'),
                      (label: '6s', value: '${bucket.batting.sixes}'),
                      (label: '50s', value: '${bucket.batting.fifties}'),
                    ]
                  : [
                      (label: 'Runs', value: '${bucket.batting.runs}'),
                      (label: 'Avg', value: Fmt.rate(bucket.batting.average)),
                      (label: 'SR', value: Fmt.rate(bucket.batting.strikeRate)),
                      (label: 'HS', value: '${bucket.batting.highest}'),
                    ],
            ),
          ],
          if (bucket.hasBowling) ...[
            const SizedBox(height: 10),
            _MiniStats(
              label: 'Bowling',
              stats: detailed
                  ? [
                      (label: 'Overs', value: bucket.bowling.overs),
                      (label: 'Wkts', value: '${bucket.bowling.wickets}'),
                      (label: 'Best', value: bucket.bowling.best),
                      (label: 'Avg', value: Fmt.rate(bucket.bowling.average)),
                      (label: 'Econ', value: Fmt.rate(bucket.bowling.economy)),
                      (label: 'Runs', value: '${bucket.bowling.runs}'),
                      (label: 'Mdns', value: '${bucket.bowling.maidens}'),
                      (label: 'Inns', value: '${bucket.bowling.innings}'),
                    ]
                  : [
                      (label: 'Wkts', value: '${bucket.bowling.wickets}'),
                      (label: 'Econ', value: Fmt.rate(bucket.bowling.economy)),
                      (label: 'Best', value: bucket.bowling.best),
                      (label: 'Overs', value: bucket.bowling.overs),
                    ],
            ),
          ],
          if (detailed && bucket.fielding.catches > 0) ...[
            const SizedBox(height: 10),
            Text(
              '${bucket.fielding.catches} '
              '${bucket.fielding.catches == 1 ? 'catch' : 'catches'} in the field',
              style: context.texts.labelSmall,
            ),
          ],
        ],
      ),
    );
  }
}

class _MiniStats extends StatelessWidget {
  final String label;
  final List<({String label, String value})> stats;

  const _MiniStats({required this.label, required this.stats});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: context.texts.labelSmall),
        const SizedBox(height: 6),
        StatGrid(columns: 4, stats: stats),
      ],
    );
  }
}

// ----------------------------------------------------------------- matches

class _Matches extends StatelessWidget {
  final PlayerHistory history;

  const _Matches({required this.history});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final m in history.matches)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: CareerMatchRow(match: m),
          ),
      ],
    );
  }
}

/// One line of a career: the fixture, and what this player did in it.
class CareerMatchRow extends StatelessWidget {
  final CareerMatch match;

  const CareerMatchRow({super.key, required this.match});

  Color _outcomeColour(BuildContext context) => switch (match.outcome) {
        'won' => context.cric.six,
        'lost' => context.cric.wicket,
        'in_progress' => context.cric.amber,
        _ => context.cric.faint,
      };

  @override
  Widget build(BuildContext context) {
    final date = Fmt.dateTime(match.playedOn).split(',').first;
    final subtitle = [
      if (match.tournament != null) match.tournament!,
      if (match.venue != null) match.venue!,
      if (date.isNotEmpty) date,
    ].join(' · ');

    return CnCard(
      onTap: () => context.push(Routes.match(match.matchId)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'v ${match.opponent}',
                  style: context.texts.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: _outcomeColour(context).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  match.outcomeLabel,
                  style: context.texts.labelSmall?.copyWith(
                    color: _outcomeColour(context),
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          if (subtitle.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: context.texts.labelSmall,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          const SizedBox(height: 10),
          // What they actually did. A player who neither batted nor bowled is
          // told so, rather than shown an empty row they have to interpret.
          if (!match.batted && !match.bowled && !match.tookAFieldingCredit)
            Text(
              match.isLive ? 'Yet to bat or bowl' : 'Did not bat or bowl',
              style: context.texts.bodySmall,
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                if (match.batted)
                  _Contribution(
                    icon: Icons.sports_cricket,
                    text: match.batLine ?? '',
                    detail: match.dismissalText,
                    highlight: match.isMilestoneInnings,
                  ),
                if (match.bowled)
                  _Contribution(
                    icon: Icons.sports_baseball_outlined,
                    text: match.bowlLine ?? '',
                    highlight: match.isStandoutSpell,
                  ),
                if (match.tookAFieldingCredit)
                  _Contribution(
                    icon: Icons.back_hand_outlined,
                    text: match.fieldingLine,
                  ),
              ],
            ),
        ],
      ),
    );
  }
}

class _Contribution extends StatelessWidget {
  final IconData icon;
  final String text;
  final String? detail;

  /// A fifty or a three-for is worth picking out of a long list.
  final bool highlight;

  const _Contribution({
    required this.icon,
    required this.text,
    this.detail,
    this.highlight = false,
  });

  @override
  Widget build(BuildContext context) {
    final colour =
        highlight ? context.scheme.primary : context.scheme.onSurface;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: highlight ? context.cric.accentSoft : context.cric.surfaceVariant,
        borderRadius: BorderRadius.circular(9),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: colour),
          const SizedBox(width: 6),
          Text(
            text,
            style: context.texts.labelMedium?.copyWith(
              color: colour,
              fontWeight: highlight ? FontWeight.w700 : FontWeight.w600,
            ),
          ),
          if (detail != null && detail!.isNotEmpty) ...[
            const SizedBox(width: 6),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 150),
              child: Text(
                detail!,
                style: context.texts.labelSmall,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
