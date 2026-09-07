import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/common.dart';
import '../players/player_providers.dart';
import '../teams/team_providers.dart';

/// Two players or two teams, side by side.
class CompareScreen extends ConsumerStatefulWidget {
  const CompareScreen({super.key});

  @override
  ConsumerState<CompareScreen> createState() => _CompareScreenState();
}

enum _Mode { players, teams }

class _CompareScreenState extends ConsumerState<CompareScreen> {
  _Mode _mode = _Mode.players;
  String? _a;
  String? _b;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Compare')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          CnSegmented<_Mode>(
            selected: _mode,
            onChanged: (v) => setState(() {
              _mode = v;
              _a = null;
              _b = null;
            }),
            options: const [
              (value: _Mode.players, label: 'Players'),
              (value: _Mode.teams, label: 'Teams'),
            ],
          ),
          const SizedBox(height: 16),
          if (_mode == _Mode.players) _playerPickers() else _teamPickers(),
          const SizedBox(height: 18),
          if (_a != null && _b != null && _a != _b)
            _mode == _Mode.players
                ? _PlayerComparison(a: _a!, b: _b!)
                : _TeamComparison(a: _a!, b: _b!)
          else
            EmptyState(
              icon: Icons.compare_arrows,
              title: _a == _b && _a != null
                  ? 'Pick two different ${_mode == _Mode.players ? 'players' : 'teams'}'
                  : 'Pick two to compare',
            ),
        ],
      ),
    );
  }

  Widget _playerPickers() {
    final players = ref.watch(playersProvider);
    return players.when(
      loading: () => const SkeletonBox(height: 60),
      error: (e, _) => ErrorState(error: e),
      data: (list) {
        if (list.length < 2) {
          return const EmptyState(
            icon: Icons.person_outline,
            title: 'Add at least two players',
          );
        }
        _a ??= list[0].id;
        _b ??= list[1].id;
        return Row(
          children: [
            Expanded(
              child: _Picker(
                label: 'Player A',
                value: _a,
                items: {for (final p in list) p.id: p.name},
                onChanged: (v) => setState(() => _a = v),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _Picker(
                label: 'Player B',
                value: _b,
                items: {for (final p in list) p.id: p.name},
                onChanged: (v) => setState(() => _b = v),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _teamPickers() {
    final teams = ref.watch(teamsProvider);
    return teams.when(
      loading: () => const SkeletonBox(height: 60),
      error: (e, _) => ErrorState(error: e),
      data: (list) {
        if (list.length < 2) {
          return const EmptyState(
            icon: Icons.groups_outlined,
            title: 'Add at least two teams',
          );
        }
        _a ??= list[0].id;
        _b ??= list[1].id;
        return Row(
          children: [
            Expanded(
              child: _Picker(
                label: 'Team A',
                value: _a,
                items: {for (final t in list) t.id: t.name},
                onChanged: (v) => setState(() => _a = v),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _Picker(
                label: 'Team B',
                value: _b,
                items: {for (final t in list) t.id: t.name},
                onChanged: (v) => setState(() => _b = v),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _Picker extends StatelessWidget {
  final String label;
  final String? value;
  final Map<String, String> items;
  final ValueChanged<String?> onChanged;

  const _Picker({
    required this.label,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label, isDense: true),
      items: [
        for (final e in items.entries)
          DropdownMenuItem(
            value: e.key,
            child: Text(e.value, overflow: TextOverflow.ellipsis),
          ),
      ],
      onChanged: onChanged,
    );
  }
}

class _PlayerComparison extends ConsumerWidget {
  final String a;
  final String b;

  const _PlayerComparison({required this.a, required this.b});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(comparePlayersProvider(ComparePair(a, b)));

    return async.when(
      loading: () => const ListSkeleton(rows: 3),
      error: (e, _) => ErrorState(error: e),
      data: (c) => Column(
        children: [
          _Heads(nameA: c.playerA.player.name, nameB: c.playerB.player.name),
          const SectionHeader(title: 'Batting'),
          _Rows(rows: [
            (
              label: 'Runs',
              a: '${c.playerA.batting.runs}',
              b: '${c.playerB.batting.runs}'
            ),
            (
              label: 'Average',
              a: Fmt.rate(c.playerA.batting.average),
              b: Fmt.rate(c.playerB.batting.average)
            ),
            (
              label: 'Strike rate',
              a: c.playerA.batting.strikeRate.toStringAsFixed(1),
              b: c.playerB.batting.strikeRate.toStringAsFixed(1)
            ),
            (
              label: 'Highest',
              a: '${c.playerA.batting.highest}',
              b: '${c.playerB.batting.highest}'
            ),
            (
              label: '50s / 100s',
              a: '${c.playerA.batting.fifties}/${c.playerA.batting.hundreds}',
              b: '${c.playerB.batting.fifties}/${c.playerB.batting.hundreds}'
            ),
            (
              label: '4s / 6s',
              a: '${c.playerA.batting.fours}/${c.playerA.batting.sixes}',
              b: '${c.playerB.batting.fours}/${c.playerB.batting.sixes}'
            ),
          ]),
          const SectionHeader(title: 'Bowling'),
          _Rows(rows: [
            (
              label: 'Wickets',
              a: '${c.playerA.bowling.wickets}',
              b: '${c.playerB.bowling.wickets}'
            ),
            (
              label: 'Economy',
              a: c.playerA.bowling.economy.toStringAsFixed(2),
              b: c.playerB.bowling.economy.toStringAsFixed(2)
            ),
            (
              label: 'Average',
              a: Fmt.rate(c.playerA.bowling.average),
              b: Fmt.rate(c.playerB.bowling.average)
            ),
            (
              label: 'Best',
              a: c.playerA.bowling.best,
              b: c.playerB.bowling.best
            ),
          ]),
        ],
      ),
    );
  }
}

class _TeamComparison extends ConsumerWidget {
  final String a;
  final String b;

  const _TeamComparison({required this.a, required this.b});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sa = ref.watch(teamStatsProvider(a)).valueOrNull;
    final sb = ref.watch(teamStatsProvider(b)).valueOrNull;
    if (sa == null || sb == null) return const ListSkeleton(rows: 2);

    return Column(
      children: [
        _Heads(nameA: sa.name, nameB: sb.name),
        const SectionHeader(title: 'Record'),
        _Rows(rows: [
          (label: 'Played', a: '${sa.played}', b: '${sb.played}'),
          (label: 'Won', a: '${sa.won}', b: '${sb.won}'),
          (label: 'Lost', a: '${sa.lost}', b: '${sb.lost}'),
          (label: 'Tied', a: '${sa.tied}', b: '${sb.tied}'),
          (
            label: 'Win %',
            a: Fmt.percent(sa.winPct, places: 0),
            b: Fmt.percent(sb.winPct, places: 0)
          ),
        ]),
        const SectionHeader(title: 'Runs'),
        _Rows(rows: [
          (label: 'Runs for', a: '${sa.runsFor}', b: '${sb.runsFor}'),
          (label: 'Runs against', a: '${sa.runsAgainst}', b: '${sb.runsAgainst}'),
          (
            label: 'Net runs',
            a: '${sa.netRuns >= 0 ? '+' : ''}${sa.netRuns}',
            b: '${sb.netRuns >= 0 ? '+' : ''}${sb.netRuns}'
          ),
        ]),
      ],
    );
  }
}

class _Heads extends StatelessWidget {
  final String nameA;
  final String nameB;

  const _Heads({required this.nameA, required this.nameB});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      child: Row(
        children: [
          Expanded(
            child: Column(
              children: [
                CnAvatar(name: nameA, size: 44),
                const SizedBox(height: 8),
                Text(
                  nameA,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  style: context.texts.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text('vs',
                style: context.texts.labelSmall
                    ?.copyWith(color: context.cric.faint)),
          ),
          Expanded(
            child: Column(
              children: [
                CnAvatar(name: nameB, size: 44),
                const SizedBox(height: 8),
                Text(
                  nameB,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  style: context.texts.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Rows extends StatelessWidget {
  final List<({String label, String a, String b})> rows;

  const _Rows({required this.rows});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      child: Column(
        children: [
          for (final r in rows)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 7),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      r.a,
                      textAlign: TextAlign.left,
                      style: context.texts.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                  Expanded(
                    flex: 2,
                    child: Text(
                      r.label,
                      textAlign: TextAlign.center,
                      style: context.texts.labelSmall
                          ?.copyWith(color: context.cric.faint),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      r.b,
                      textAlign: TextAlign.right,
                      style: context.texts.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
