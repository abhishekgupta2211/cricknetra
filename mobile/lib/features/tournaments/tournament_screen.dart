import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_config.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/roster.dart';
import '../../core/models/social.dart';
import '../../core/models/tournament.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../players/player_providers.dart';
import '../social/follow_button.dart';
import 'tournament_providers.dart';

/// A tournament: points table or bracket, fixtures, and the squads.
class TournamentScreen extends ConsumerWidget {
  final String tournamentId;

  const TournamentScreen({super.key, required this.tournamentId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(tournamentProvider(tournamentId));
    final auth = ref.watch(authControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(async.valueOrNull?.name ?? 'Tournament'),
        actions: [
          IconButton(
            tooltip: 'Share',
            icon: const Icon(Icons.ios_share, size: 20),
            onPressed: () => context.copyToClipboard(
              ApiConfig.tournamentShareUrl(tournamentId),
              message: 'Share link copied',
            ),
          ),
          if (auth.isAdmin)
            IconButton(
              icon: const Icon(Icons.delete_outline, size: 21),
              onPressed: () async {
                final ok = await confirmDialog(
                  context,
                  title: 'Delete this tournament?',
                  message: 'Fixtures and standings go with it.',
                );
                if (!ok) return;
                try {
                  await ref.read(apiProvider).deleteTournament(tournamentId);
                  ref.invalidate(tournamentsProvider);
                  if (context.mounted) context.pop();
                } catch (e) {
                  if (context.mounted) context.toastError(e);
                }
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
          onRetry: () => ref.invalidate(tournamentProvider(tournamentId)),
        ),
        data: (t) => RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(tournamentProvider(tournamentId));
            ref.invalidate(tournamentSquadsProvider(tournamentId));
          },
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              _Header(tournament: t),
              if (t.champion != null) ...[
                const SizedBox(height: 14),
                _ChampionBanner(champion: t.champion!),
              ],
              const SizedBox(height: 14),
              if (t.isGroups)
                ..._groupsView(context, t)
              else if (t.isKnockout)
                ..._knockoutView(context, t)
              else
                ..._leagueView(context, t),
              const SizedBox(height: 8),
              _SquadsSection(
                tournamentId: tournamentId,
                canManage: auth.can(Caps.createTournament),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _leagueView(BuildContext context, Tournament t) {
    final rounds = t.roundsOf(t.fixtures);
    return [
      if (t.standings.isNotEmpty) ...[
        PointsTable(rows: t.standings),
        const SizedBox(height: 14),
      ],
      for (final entry in rounds.entries) ...[
        SectionHeader(title: 'Round ${entry.key}'),
        for (final f in entry.value)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: FixtureCard(fixture: f, tournamentId: t.id),
          ),
      ],
    ];
  }

  List<Widget> _knockoutView(BuildContext context, Tournament t) {
    final rounds = t.roundsOf(t.bracketFixtures);
    final total = rounds.keys.isEmpty
        ? 1
        : rounds.keys.reduce((a, b) => a > b ? a : b);
    return [
      for (final entry in rounds.entries) ...[
        SectionHeader(
          title: Tournament.roundLabel(entry.key, total),
        ),
        for (final f in entry.value)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: FixtureCard(fixture: f, tournamentId: t.id),
          ),
      ],
    ];
  }

  List<Widget> _groupsView(BuildContext context, Tournament t) {
    final bracket = t.bracketFixtures;
    return [
      for (final g in t.groups) ...[
        SectionHeader(title: 'Group ${g.group}'),
        PointsTable(rows: g.standings),
        const SizedBox(height: 12),
        for (final f in t.fixturesInGroup(g.group))
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: FixtureCard(fixture: f, tournamentId: t.id),
          ),
      ],
      const SectionHeader(title: 'Playoffs'),
      if (bracket.isEmpty)
        CnCard(
          child: Text(
            'The playoffs are seeded once every group game is played.',
            style: context.texts.bodySmall,
          ),
        )
      else
        for (final f in bracket)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: FixtureCard(fixture: f, tournamentId: t.id),
          ),
    ];
  }
}

class _Header extends StatelessWidget {
  final Tournament tournament;

  const _Header({required this.tournament});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(tournament.name, style: context.texts.headlineSmall),
              const SizedBox(height: 4),
              Row(
                children: [
                  CnBadge(
                      text: TournamentFormats.label(tournament.format)),
                  const SizedBox(width: 6),
                  Text('${tournament.teams.length} teams',
                      style: context.texts.bodySmall),
                  if (tournament.dlsEnabled) ...[
                    const SizedBox(width: 6),
                    const CnBadge(text: 'DLS'),
                  ],
                ],
              ),
            ],
          ),
        ),
        FollowButton(
          entityType: FollowEntities.tournament,
          entityId: tournament.id,
        ),
      ],
    );
  }
}

class _ChampionBanner extends StatelessWidget {
  final TeamRef champion;

  const _ChampionBanner({required this.champion});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      color: context.cric.amberSoft,
      borderColor: context.cric.amber.withValues(alpha: 0.35),
      child: Row(
        children: [
          Icon(Icons.emoji_events, size: 26, color: context.cric.amber),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Champion', style: context.texts.labelSmall),
                Text(champion.name, style: context.texts.titleMedium),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// A league table, sorted by points then net run rate.
class PointsTable extends StatelessWidget {
  final List<StandingRow> rows;

  const PointsTable({super.key, required this.rows});

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) return const SizedBox.shrink();

    final head = context.texts.labelSmall?.copyWith(
      color: context.cric.faint,
      fontWeight: FontWeight.w700,
    );

    Widget cell(String v, {bool bold = false}) => SizedBox(
          width: 30,
          child: Text(
            v,
            textAlign: TextAlign.right,
            style: context.texts.bodySmall?.copyWith(
              fontWeight: bold ? FontWeight.w700 : null,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
        );

    return CnCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(child: Text('TEAM', style: head)),
              SizedBox(width: 30, child: Text('P', textAlign: TextAlign.right, style: head)),
              SizedBox(width: 30, child: Text('W', textAlign: TextAlign.right, style: head)),
              SizedBox(width: 30, child: Text('L', textAlign: TextAlign.right, style: head)),
              SizedBox(width: 30, child: Text('Pts', textAlign: TextAlign.right, style: head)),
              SizedBox(width: 54, child: Text('NRR', textAlign: TextAlign.right, style: head)),
            ],
          ),
          Divider(height: 14, color: context.cric.line),
          for (var i = 0; i < rows.length; i++)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Row(
                children: [
                  SizedBox(
                    width: 20,
                    child: Text('${i + 1}',
                        style: context.texts.labelSmall
                            ?.copyWith(color: context.cric.faint)),
                  ),
                  Expanded(
                    child: Text(
                      rows[i].name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.texts.bodySmall,
                    ),
                  ),
                  cell('${rows[i].played}'),
                  cell('${rows[i].won}'),
                  cell('${rows[i].lost}'),
                  cell('${rows[i].points}', bold: true),
                  SizedBox(
                    width: 54,
                    child: Text(
                      rows[i].nrrText,
                      textAlign: TextAlign.right,
                      style: context.texts.bodySmall?.copyWith(
                        color: rows[i].nrr >= 0
                            ? context.scheme.primary
                            : context.cric.wicket,
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

/// One fixture, with the control to start it when it is still scheduled.
class FixtureCard extends ConsumerWidget {
  final Fixture fixture;
  final String tournamentId;

  const FixtureCard({
    super.key,
    required this.fixture,
    required this.tournamentId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final canManage =
        ref.watch(authControllerProvider).can(Caps.createTournament);

    return CnCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      onTap: fixture.matchId == null
          ? null
          : () => context.push(Routes.match(fixture.matchId!)),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  fixture.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
                if (fixture.result != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    fixture.result!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.texts.bodySmall,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 10),
          if (fixture.isBye)
            CnBadge(text: 'Bye', color: context.cric.muted)
          else if (fixture.isLive)
            CnBadge(text: 'LIVE', color: context.cric.wicket)
          else if (fixture.isCompleted)
            CnBadge(text: 'Result', color: context.cric.muted)
          else if (canManage && fixture.teamA != null && fixture.teamB != null)
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(0, 34),
                padding: const EdgeInsets.symmetric(horizontal: 14),
              ),
              onPressed: () => _startFixture(context, ref),
              child: const Text('Start'),
            )
          else
            CnBadge(text: 'Scheduled', color: context.cric.faint),
        ],
      ),
    );
  }

  Future<void> _startFixture(BuildContext context, WidgetRef ref) async {
    final result = await showModalBottomSheet<Fixture>(
      context: context,
      isScrollControlled: true,
      builder: (context) => _StartFixtureSheet(
        fixture: fixture,
        tournamentId: tournamentId,
      ),
    );
    if (result == null || !context.mounted) return;
    ref.invalidate(tournamentProvider(tournamentId));
    if (result.matchId != null) {
      context.push(Routes.match(result.matchId!));
    }
  }
}

/// Pick both XIs and who bats first, then create the match.
class _StartFixtureSheet extends ConsumerStatefulWidget {
  final Fixture fixture;
  final String tournamentId;

  const _StartFixtureSheet({
    required this.fixture,
    required this.tournamentId,
  });

  @override
  ConsumerState<_StartFixtureSheet> createState() =>
      _StartFixtureSheetState();
}

class _StartFixtureSheetState extends ConsumerState<_StartFixtureSheet> {
  final _squadA = <String>{};
  final _squadB = <String>{};
  String _batFirst = 'a';
  bool _busy = false;

  // Both pools are resolved once. Building the futures inside build() would
  // hand the FutureBuilder a new future on every checkbox tap, so the lists
  // would blink back to skeletons and refetch on each selection.
  List<Player>? _poolA;
  List<Player>? _poolB;
  Object? _poolError;

  @override
  void initState() {
    super.initState();
    _loadPools();
  }

  Future<void> _loadPools() async {
    final a = widget.fixture.teamA;
    final b = widget.fixture.teamB;
    if (a == null || b == null) return;
    setState(() {
      _poolError = null;
      _poolA = null;
      _poolB = null;
    });
    try {
      final pools = await Future.wait([_poolFor(a.id), _poolFor(b.id)]);
      if (!mounted) return;
      setState(() {
        _poolError = null;
        _poolA = pools[0];
        _poolB = pools[1];
        // Start with the whole squad selected, the usual case.
        _squadA.addAll(pools[0].map((p) => p.id));
        _squadB.addAll(pools[1].map((p) => p.id));
      });
    } catch (e) {
      if (mounted) setState(() => _poolError = e);
    }
  }

  /// The tournament squad if one is registered, otherwise the team's own list.
  Future<List<Player>> _poolFor(String teamId) async {
    // Await rather than reading a snapshot: right after a pull-to-refresh the
    // value is null, and falling through would offer the whole roster instead
    // of the registered squad.
    List<TeamSquad>? squads;
    try {
      squads = await ref.read(tournamentSquadsProvider(widget.tournamentId).future);
    } catch (_) {
      squads = null;
    }
    if (squads != null) {
      for (final s in squads) {
        if (s.teamId == teamId && s.players.isNotEmpty) return s.players;
      }
    }
    final team = await ref.read(apiProvider).team(teamId);
    return team.members
        .map((m) => Player(id: m.playerId, name: m.name, code: m.code))
        .toList();
  }

  Future<void> _start() async {
    if (_squadA.length < 2 || _squadB.length < 2) {
      context.toast('Pick at least two players per side');
      return;
    }
    if (_squadA.length != _squadB.length) {
      context.toast('Both sides need the same number of players');
      return;
    }
    setState(() => _busy = true);
    try {
      final started = await ref.read(apiProvider).startFixture(
            widget.fixture.id,
            squadAIds: _squadA.toList(),
            squadBIds: _squadB.toList(),
            batFirst: _batFirst,
          );
      if (!mounted) return;
      Navigator.pop(context, started);
    } catch (e) {
      if (!mounted) return;
      context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final a = widget.fixture.teamA;
    final b = widget.fixture.teamB;
    if (a == null || b == null) return const SizedBox.shrink();

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.9,
      builder: (context, controller) => ListView(
        controller: controller,
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        children: [
          Text(widget.fixture.title, style: context.texts.titleMedium),
          const SizedBox(height: 16),
          if (_poolError != null)
            ErrorState(error: _poolError!, onRetry: _loadPools)
          else ...[
            _SquadColumn(
              title: a.name,
              pool: _poolA,
              chosen: _squadA,
              onChanged: () => setState(() {}),
            ),
            const SizedBox(height: 16),
            _SquadColumn(
              title: b.name,
              pool: _poolB,
              chosen: _squadB,
              onChanged: () => setState(() {}),
            ),
          ],
          const SizedBox(height: 18),
          Text('Bats first', style: context.texts.labelLarge),
          const SizedBox(height: 8),
          CnSegmented<String>(
            selected: _batFirst,
            onChanged: (v) => setState(() => _batFirst = v),
            options: [
              (value: 'a', label: a.name),
              (value: 'b', label: b.name),
            ],
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: _busy ? null : _start,
            child: const Text('Start and score'),
          ),
        ],
      ),
    );
  }
}

class _SquadColumn extends StatelessWidget {
  final String title;

  /// Null while the pool is still loading.
  final List<Player>? pool;
  final Set<String> chosen;
  final VoidCallback onChanged;

  const _SquadColumn({
    required this.title,
    required this.pool,
    required this.chosen,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final players = pool;
    if (players == null) {
      return const CnCard(child: SkeletonBox(height: 60));
    }
    if (players.isEmpty) {
      return CnCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: context.texts.titleSmall),
            const SizedBox(height: 6),
            Text(
              'No squad registered for this team. Add players in the '
              'Squads section below.',
              style: context.texts.bodySmall,
            ),
          ],
        ),
      );
    }

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(child: Text(title, style: context.texts.titleSmall)),
              Text('${chosen.length} picked', style: context.texts.labelSmall),
            ],
          ),
          for (final p in players)
            CheckboxListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: chosen.contains(p.id),
              onChanged: (v) {
                if (v == true) {
                  chosen.add(p.id);
                } else {
                  chosen.remove(p.id);
                }
                onChanged();
              },
              title: Text(p.name, style: context.texts.bodyMedium),
            ),
        ],
      ),
    );
  }
}

/// Per-tournament squads. A player may only be registered to one team.
class _SquadsSection extends ConsumerWidget {
  final String tournamentId;
  final bool canManage;

  const _SquadsSection({required this.tournamentId, required this.canManage});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final squads = ref.watch(tournamentSquadsProvider(tournamentId)).valueOrNull;
    if (squads == null || squads.isEmpty) return const SizedBox.shrink();

    // One player, one team per tournament — so anyone already registered
    // elsewhere is out of the pool.
    final taken = <String, String>{};
    for (final s in squads) {
      for (final p in s.players) {
        taken[p.id] = s.teamName;
      }
    }

    return Column(
      children: [
        const SectionHeader(title: 'Squads'),
        for (final s in squads)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: CnCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(s.teamName,
                            style: context.texts.titleSmall),
                      ),
                      Text('${s.players.length} players',
                          style: context.texts.labelSmall),
                    ],
                  ),
                  const SizedBox(height: 8),
                  if (s.players.isEmpty)
                    Text('No players registered yet.',
                        style: context.texts.bodySmall)
                  else
                    for (final p in s.players)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 3),
                        child: Row(
                          children: [
                            CnAvatar(name: p.name, size: 28),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(p.name,
                                  style: context.texts.bodySmall),
                            ),
                            if (canManage)
                              IconButton(
                                iconSize: 16,
                                visualDensity: VisualDensity.compact,
                                icon: const Icon(Icons.remove_circle_outline),
                                onPressed: () async {
                                  try {
                                    await ref
                                        .read(apiProvider)
                                        .unregisterSquadPlayer(
                                            tournamentId, s.teamId, p.id);
                                    ref.invalidate(tournamentSquadsProvider(
                                        tournamentId));
                                  } catch (e) {
                                    if (context.mounted) {
                                      context.toastError(e);
                                    }
                                  }
                                },
                              ),
                          ],
                        ),
                      ),
                  if (canManage) ...[
                    const SizedBox(height: 8),
                    OutlinedButton.icon(
                      onPressed: () =>
                          _register(context, ref, s.teamId, taken),
                      icon: const Icon(Icons.person_add_alt, size: 17),
                      label: const Text('Register a player'),
                    ),
                  ],
                ],
              ),
            ),
          ),
      ],
    );
  }

  Future<void> _register(
    BuildContext context,
    WidgetRef ref,
    String teamId,
    Map<String, String> taken,
  ) async {
    final pool = ref.read(playersProvider).valueOrNull ?? const <Player>[];
    final free = pool.where((p) => !taken.containsKey(p.id)).toList();
    if (free.isEmpty) {
      context.toast('Every player is already registered to a team');
      return;
    }

    final picked = await showModalBottomSheet<Player>(
      context: context,
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.7,
        builder: (context, controller) => ListView.builder(
          controller: controller,
          itemCount: free.length,
          itemBuilder: (context, i) => ListTile(
            leading: CnAvatar(name: free[i].name, size: 32),
            title: Text(free[i].name),
            subtitle: Text(free[i].code),
            onTap: () => Navigator.pop(context, free[i]),
          ),
        ),
      ),
    );
    if (picked == null || !context.mounted) return;

    try {
      await ref
          .read(apiProvider)
          .registerSquadPlayer(tournamentId, teamId, picked.id);
      ref.invalidate(tournamentSquadsProvider(tournamentId));
    } catch (e) {
      if (context.mounted) context.toastError(e);
    }
  }
}
