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
import '../players/player_providers.dart';
import '../social/follow_button.dart';
import 'team_providers.dart';

/// One team: its record, its squad, and the controls to manage both.
class TeamScreen extends ConsumerWidget {
  final String teamId;

  const TeamScreen({super.key, required this.teamId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(teamProvider(teamId));
    final auth = ref.watch(authControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(async.valueOrNull?.name ?? 'Team'),
        actions: [
          if (auth.isAdmin)
            IconButton(
              icon: const Icon(Icons.delete_outline, size: 21),
              tooltip: 'Delete team',
              onPressed: () async {
                final ok = await confirmDialog(
                  context,
                  title: 'Delete this team?',
                  message: 'Matches already played keep their scorecards.',
                );
                if (!ok) return;
                try {
                  await ref.read(apiProvider).deleteTeam(teamId);
                  ref.invalidate(teamsProvider);
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
          onRetry: () => ref.invalidate(teamProvider(teamId)),
        ),
        data: (team) => RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(teamProvider(teamId));
            ref.invalidate(teamStatsProvider(teamId));
          },
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              _Header(team: team),
              const SizedBox(height: 14),
              _RecordCard(teamId: teamId),
              const SizedBox(height: 14),
              _SquadCard(
                team: team,
                canManage: auth.can(Caps.createTeam) || auth.isAdmin,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  final Team team;

  const _Header({required this.team});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        CnAvatar(
          name: team.name,
          size: 60,
          imageUrl: team.hasPhoto ? ApiConfig.teamPhoto(team.id) : null,
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(team.name, style: context.texts.headlineSmall),
              const SizedBox(height: 2),
              Text(team.subtitle, style: context.texts.bodySmall),
            ],
          ),
        ),
        FollowButton(
          entityType: FollowEntities.team,
          entityId: team.id,
        ),
      ],
    );
  }
}

class _RecordCard extends ConsumerWidget {
  final String teamId;

  const _RecordCard({required this.teamId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(teamStatsProvider(teamId)).valueOrNull;
    if (stats == null || stats.played == 0) {
      return CnCard(
        child: Row(
          children: [
            Icon(Icons.query_stats, size: 18, color: context.cric.faint),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'No completed matches yet. The record fills in as they finish.',
                style: context.texts.bodySmall,
              ),
            ),
          ],
        ),
      );
    }

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Record', style: context.texts.titleSmall),
          const SizedBox(height: 14),
          StatGrid(
            columns: 5,
            stats: [
              (label: 'Played', value: '${stats.played}'),
              (label: 'Won', value: '${stats.won}'),
              (label: 'Lost', value: '${stats.lost}'),
              (label: 'Tied', value: '${stats.tied}'),
              (label: 'Win %', value: Fmt.percent(stats.winPct, places: 0)),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Runs for ${stats.runsFor} · against ${stats.runsAgainst}',
            style: context.texts.bodySmall,
          ),
        ],
      ),
    );
  }
}

class _SquadCard extends ConsumerStatefulWidget {
  final Team team;
  final bool canManage;

  const _SquadCard({required this.team, required this.canManage});

  @override
  ConsumerState<_SquadCard> createState() => _SquadCardState();
}

class _SquadCardState extends ConsumerState<_SquadCard> {
  bool _busy = false;

  /// Players in the roster who are not already in this squad.
  List<Player> _available(List<Player> pool) {
    final inSquad = widget.team.members.map((m) => m.playerId).toSet();
    return pool.where((p) => !inSquad.contains(p.id)).toList();
  }

  Future<void> _addExisting() async {
    // Await the roster rather than reading a possibly-unresolved snapshot; a
    // plain read here returns null on first open and looks like an empty pool.
    List<Player> pool;
    try {
      pool = await ref.read(playersProvider.future);
    } catch (e) {
      if (mounted) context.toastError(e);
      return;
    }
    if (!mounted) return;

    final available = _available(pool);
    if (available.isEmpty) {
      context.toast(pool.isEmpty
          ? 'No players in the roster yet. Create one instead.'
          : 'Every player in your roster is already in this squad');
      return;
    }

    final picked = await showModalBottomSheet<Player>(
      context: context,
      isScrollControlled: true,
      builder: (context) => _PlayerPickerSheet(players: available),
    );
    if (picked == null || !mounted) return;
    await _run(() => ref
        .read(apiProvider)
        .addTeamMember(widget.team.id, playerId: picked.id));
  }

  Future<void> _addNew() async {
    final name = await promptDialog(
      context,
      title: 'New player',
      hint: 'Player name',
      confirmLabel: 'Add',
    );
    if (name == null || !mounted) return;
    await _run(
      () => ref.read(apiProvider).addTeamMember(widget.team.id, name: name),
    );
  }

  Future<void> _run(Future<Team> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
      ref.invalidate(teamProvider(widget.team.id));
      ref.invalidate(playersProvider);
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final members = widget.team.members;

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text('Squad (${members.length})',
                    style: context.texts.titleSmall),
              ),
              if (widget.canManage)
                PopupMenuButton<String>(
                  enabled: !_busy,
                  icon: const Icon(Icons.person_add_alt, size: 20),
                  onSelected: (v) =>
                      v == 'existing' ? _addExisting() : _addNew(),
                  itemBuilder: (context) => const [
                    PopupMenuItem(
                      value: 'existing',
                      child: Text('Add from roster'),
                    ),
                    PopupMenuItem(
                      value: 'new',
                      child: Text('Create a new player'),
                    ),
                  ],
                ),
            ],
          ),
          const SizedBox(height: 8),
          if (members.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Text(
                'No players yet. Add some so you can pick an XI at match time.',
                style: context.texts.bodySmall,
              ),
            )
          else
            for (final m in members)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    CnAvatar(
                      name: m.name,
                      size: 34,
                      imageUrl: m.hasPhoto
                          ? ApiConfig.playerPhoto(m.playerId)
                          : null,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: InkWell(
                        onTap: () => context.push(Routes.player(m.playerId)),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Flexible(
                                  child: Text(
                                    m.name,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: context.texts.bodyMedium,
                                  ),
                                ),
                                if (m.isCaptain) ...[
                                  const SizedBox(width: 6),
                                  const CnBadge(text: 'C'),
                                ],
                              ],
                            ),
                            if (m.code.isNotEmpty)
                              Text(m.code, style: context.texts.labelSmall),
                          ],
                        ),
                      ),
                    ),
                    if (widget.canManage)
                      IconButton(
                        iconSize: 17,
                        visualDensity: VisualDensity.compact,
                        icon: const Icon(Icons.remove_circle_outline),
                        onPressed: _busy
                            ? null
                            : () => _run(() => ref
                                .read(apiProvider)
                                .removeTeamMember(
                                    widget.team.id, m.playerId)),
                      ),
                  ],
                ),
              ),
        ],
      ),
    );
  }
}

/// A searchable list of roster players.
class _PlayerPickerSheet extends StatefulWidget {
  final List<Player> players;

  const _PlayerPickerSheet({required this.players});

  @override
  State<_PlayerPickerSheet> createState() => _PlayerPickerSheetState();
}

class _PlayerPickerSheetState extends State<_PlayerPickerSheet> {
  final _search = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final q = _query.trim().toLowerCase();
    final list = widget.players.where((p) {
      if (q.isEmpty) return true;
      return p.name.toLowerCase().contains(q) ||
          p.code.toLowerCase().contains(q);
    }).toList();

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.7,
      builder: (context, controller) => Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
            child: SearchField(
              controller: _search,
              hint: 'Search by name or code',
              autofocus: true,
              onChanged: (v) => setState(() => _query = v),
            ),
          ),
          Expanded(
            child: ListView.builder(
              controller: controller,
              itemCount: list.length,
              itemBuilder: (context, i) {
                final p = list[i];
                return ListTile(
                  leading: CnAvatar(name: p.name, size: 34),
                  title: Text(p.name),
                  subtitle: Text(p.code.isEmpty ? p.styleLine : p.code),
                  onTap: () => Navigator.pop(context, p),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
