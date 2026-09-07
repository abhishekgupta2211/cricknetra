import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/roster.dart';
import '../../core/models/rules.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../auth/login_screen.dart';
import '../rules/rule_providers.dart';
import '../teams/team_providers.dart';

/// Set up a match: two sides, a rulebook, and optionally the real players so
/// the innings feeds everyone's career stats.
class CreateMatchScreen extends ConsumerStatefulWidget {
  const CreateMatchScreen({super.key});

  @override
  ConsumerState<CreateMatchScreen> createState() => _CreateMatchScreenState();
}

enum _Mode { quick, fromTeams }

class _CreateMatchScreenState extends ConsumerState<CreateMatchScreen> {
  final _teamAName = TextEditingController(text: 'Strikers');
  final _teamBName = TextEditingController(text: 'Blasters');
  final _venue = TextEditingController();
  final _tournament = TextEditingController();
  final _matchNo = TextEditingController();

  _Mode _mode = _Mode.quick;

  /// Either a preset id, or `template:<id>` for a saved rulebook.
  String _formatChoice = 't20';
  String _batFirst = 'a';
  String? _tossWinner;
  String? _tossDecision;

  Team? _teamA;
  Team? _teamB;
  final _squadA = <String>{};
  final _squadB = <String>{};
  // Real names, reported by the squad pickers from the per-team detail fetch.
  // The summary list can lag behind it after a player is added elsewhere.
  final _namesA = <String, String>{};
  final _namesB = <String, String>{};
  // Which team each side's selection was seeded from, so it is seeded exactly
  // once per team and survives the picker being rebuilt.
  String? _seededA;
  String? _seededB;

  bool _showDetails = false;
  bool _busy = false;

  @override
  void dispose() {
    _teamAName.dispose();
    _teamBName.dispose();
    _venue.dispose();
    _tournament.dispose();
    _matchNo.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);

    if (!auth.can(Caps.createMatch)) {
      return Scaffold(
        appBar: AppBar(title: const Text('New match')),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: GateCard(
            what: 'score a match',
            signedIn: auth.isSignedIn,
            role: auth.user?.role,
            onSignIn: () => context.push(Routes.login),
            onRegister: () => context.push(Routes.register),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('New match')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          CnSegmented<_Mode>(
            selected: _mode,
            onChanged: (v) => setState(() => _mode = v),
            options: const [
              (value: _Mode.quick, label: 'Quick'),
              (value: _Mode.fromTeams, label: 'From teams'),
            ],
          ),
          const SizedBox(height: 16),
          if (_mode == _Mode.quick) _quickForm() else _teamsForm(),
          const SizedBox(height: 14),
          _formatCard(),
          const SizedBox(height: 14),
          _detailsCard(),
          const SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: _busy ? null : _create,
            icon: _busy
                ? const ButtonSpinner()
                : const Icon(Icons.play_arrow, size: 20),
            label: Text(_busy ? 'Creating' : 'Create and score'),
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------ quick mode

  Widget _quickForm() {
    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Teams', style: context.texts.titleSmall),
          const SizedBox(height: 12),
          TextField(
            controller: _teamAName,
            decoration: const InputDecoration(
                labelText: 'Team A', isDense: true),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _teamBName,
            decoration: const InputDecoration(
                labelText: 'Team B', isDense: true),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 14),
          _batFirstPicker(_teamAName.text, _teamBName.text),
          const SizedBox(height: 10),
          Text(
            'Squads are generated automatically. Use "From teams" to pick real '
            'players so the match counts toward their career stats.',
            style: context.texts.labelSmall?.copyWith(color: context.cric.faint),
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------- from-teams mode

  Widget _teamsForm() {
    final teams = ref.watch(teamsProvider);

    return teams.when(
      loading: () => const CnCard(child: SkeletonBox(height: 90)),
      error: (e, _) => CnCard(child: ErrorState(error: e)),
      data: (list) {
        if (list.length < 2) {
          return CnCard(
            child: EmptyState(
              icon: Icons.groups_outlined,
              title: 'You need two teams',
              message:
                  'Create teams and add players, then come back to pick the XIs.',
              actionLabel: 'Go to teams',
              onAction: () => context.push(Routes.teams),
            ),
          );
        }

        // Seed the pickers the first time the list arrives.
        _teamA ??= list[0];
        _teamB ??= list.length > 1 ? list[1] : list[0];

        return Column(
          children: [
            _TeamSquadPicker(
              label: 'Team A',
              teams: list,
              selected: _teamA!,
              chosen: _squadA,
              seededTeamId: _seededA,
              onTeamChanged: (t) => setState(() {
                _teamA = t;
                _squadA.clear();
                _namesA.clear();
                _seededA = null;
              }),
              onChosenChanged: () => setState(() {}),
              onSeeded: (teamId, names) {
                _seededA = teamId;
                _namesA
                  ..clear()
                  ..addAll(names);
              },
            ),
            const SizedBox(height: 12),
            _TeamSquadPicker(
              label: 'Team B',
              teams: list,
              selected: _teamB!,
              chosen: _squadB,
              seededTeamId: _seededB,
              onTeamChanged: (t) => setState(() {
                _teamB = t;
                _squadB.clear();
                _namesB.clear();
                _seededB = null;
              }),
              onChosenChanged: () => setState(() {}),
              onSeeded: (teamId, names) {
                _seededB = teamId;
                _namesB
                  ..clear()
                  ..addAll(names);
              },
            ),
            const SizedBox(height: 12),
            CnCard(
              child: _batFirstPicker(_teamA!.name, _teamB!.name),
            ),
          ],
        );
      },
    );
  }

  Widget _batFirstPicker(String a, String b) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Bats first', style: context.texts.labelLarge),
        const SizedBox(height: 8),
        CnSegmented<String>(
          selected: _batFirst,
          onChanged: (v) => setState(() => _batFirst = v),
          options: [
            (value: 'a', label: a.isEmpty ? 'Team A' : a),
            (value: 'b', label: b.isEmpty ? 'Team B' : b),
          ],
        ),
      ],
    );
  }

  // --------------------------------------------------------- format & rules

  Widget _formatCard() {
    final presets = ref.watch(presetsProvider);
    final templates = ref.watch(ruleTemplatesProvider);

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text('Format and rules',
                    style: context.texts.titleSmall),
              ),
              TextButton(
                onPressed: () => context.push(Routes.rules),
                child: const Text('Build rules'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            initialValue: _formatChoice,
            isExpanded: true,
            decoration: const InputDecoration(isDense: true),
            items: [
              ...presets.maybeWhen(
                data: (list) => [
                  for (final p in list)
                    DropdownMenuItem(
                      value: p.id,
                      child: Text('${p.name} — ${p.summaryLine}',
                          overflow: TextOverflow.ellipsis),
                    ),
                ],
                orElse: () => const <DropdownMenuItem<String>>[],
              ),
              ...templates.maybeWhen(
                data: (list) => [
                  for (final t in list)
                    DropdownMenuItem(
                      value: 'template:${t.id}',
                      child: Text('${t.name} — ${t.summary}',
                          overflow: TextOverflow.ellipsis),
                    ),
                ],
                orElse: () => const <DropdownMenuItem<String>>[],
              ),
            ],
            onChanged: (v) => setState(() => _formatChoice = v ?? _formatChoice),
          ),
        ],
      ),
    );
  }

  Widget _detailsCard() {
    final a = _mode == _Mode.quick ? _teamAName.text : (_teamA?.name ?? 'Team A');
    final b = _mode == _Mode.quick ? _teamBName.text : (_teamB?.name ?? 'Team B');

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          InkWell(
            onTap: () => setState(() => _showDetails = !_showDetails),
            child: Row(
              children: [
                Expanded(
                  child: Text('Match details (optional)',
                      style: context.texts.titleSmall),
                ),
                Icon(
                  _showDetails ? Icons.expand_less : Icons.expand_more,
                  size: 20,
                  color: context.cric.faint,
                ),
              ],
            ),
          ),
          if (_showDetails) ...[
            const SizedBox(height: 14),
            TextField(
              controller: _venue,
              maxLength: 120,
              decoration: const InputDecoration(
                labelText: 'Venue',
                isDense: true,
                counterText: '',
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _tournament,
              maxLength: 120,
              decoration: const InputDecoration(
                labelText: 'Tournament',
                isDense: true,
                counterText: '',
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _matchNo,
              maxLength: 40,
              decoration: const InputDecoration(
                labelText: 'Match number',
                isDense: true,
                counterText: '',
              ),
            ),
            const SizedBox(height: 14),
            Text('Toss', style: context.texts.labelLarge),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String?>(
                    initialValue: _tossWinner,
                    isExpanded: true,
                    decoration: const InputDecoration(
                        labelText: 'Won by', isDense: true),
                    items: [
                      const DropdownMenuItem<String?>(
                          value: null, child: Text('—')),
                      DropdownMenuItem(
                          value: 'a',
                          child: Text(a, overflow: TextOverflow.ellipsis)),
                      DropdownMenuItem(
                          value: 'b',
                          child: Text(b, overflow: TextOverflow.ellipsis)),
                    ],
                    onChanged: (v) => setState(() => _tossWinner = v),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: DropdownButtonFormField<String?>(
                    initialValue: _tossDecision,
                    isExpanded: true,
                    decoration: const InputDecoration(
                        labelText: 'Chose to', isDense: true),
                    items: const [
                      DropdownMenuItem<String?>(value: null, child: Text('—')),
                      DropdownMenuItem(value: 'bat', child: Text('Bat')),
                      DropdownMenuItem(value: 'bowl', child: Text('Bowl')),
                    ],
                    onChanged: (v) => setState(() => _tossDecision = v),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  // -------------------------------------------------------------- creation

  /// Player names for the chosen ids, keeping the caller's order.
  ///
  /// Prefers what the per-team detail fetch reported; the summary list is only
  /// a backstop, because it can be stale after a player is added elsewhere.
  List<String> _namesFor(
    Team team,
    List<String> ids,
    Map<String, String> loaded,
  ) {
    final byId = {
      for (final m in team.members) m.playerId: m.name,
      ...loaded,
    };
    return [for (final id in ids) byId[id] ?? id];
  }

  Future<void> _create() async {
    final api = ref.read(apiProvider);

    // Validate everything first, so no complaint has to cross an async gap.
    String teamA;
    String teamB;
    List<String>? squadANames;
    List<String>? squadBNames;
    List<String>? squadAIds;
    List<String>? squadBIds;
    String? teamAId;
    String? teamBId;

    if (_mode == _Mode.quick) {
      teamA = _teamAName.text.trim();
      teamB = _teamBName.text.trim();
      if (teamA.isEmpty || teamB.isEmpty) {
        context.toast('Name both teams');
        return;
      }
    } else {
      if (_teamA == null || _teamB == null) return;
      if (_teamA!.id == _teamB!.id) {
        context.toast('Pick two different teams');
        return;
      }
      if (_squadA.length < 2 || _squadB.length < 2) {
        context.toast('Pick at least two players per side');
        return;
      }
      if (_squadA.length != _squadB.length) {
        context.toast('Both sides need the same number of players');
        return;
      }
      teamA = _teamA!.name;
      teamB = _teamB!.name;
      teamAId = _teamA!.id;
      teamBId = _teamB!.id;
      squadAIds = _squadA.toList();
      squadBIds = _squadB.toList();
      // Send the names in the same order, so the scorecard reads properly.
      // The names come from the detail fetch, which can hold a player the
      // summary list has not caught up with, so look up defensively.
      squadANames = _namesFor(_teamA!, squadAIds, _namesA);
      squadBNames = _namesFor(_teamB!, squadBIds, _namesB);
    }

    setState(() => _busy = true);
    try {
      // A saved template ships its whole rulebook; a preset only needs its id.
      var formatId = 't20';
      MatchRules? rules;
      if (_formatChoice.startsWith('template:')) {
        final template = await api
            .ruleTemplate(_formatChoice.substring('template:'.length));
        rules = template.rules;
      } else {
        formatId = _formatChoice;
      }

      final match = await api.createMatch(
        teamA: teamA,
        teamB: teamB,
        formatId: formatId,
        rules: rules,
        batFirst: _batFirst,
        squadA: squadANames,
        squadB: squadBNames,
        squadAIds: squadAIds,
        squadBIds: squadBIds,
        teamAId: teamAId,
        teamBId: teamBId,
        venue: _venue.text.trim(),
        tournament: _tournament.text.trim(),
        matchNo: _matchNo.text.trim(),
        tossWinner: _tossWinner,
        tossDecision: _tossDecision,
      );
      if (!mounted) return;
      context.pushReplacement(Routes.match(match.id));
    } catch (e) {
      if (!mounted) return;
      context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

/// Pick a team, then tick the players in its XI.
class _TeamSquadPicker extends ConsumerStatefulWidget {
  final String label;
  final List<Team> teams;
  final Team selected;
  final Set<String> chosen;
  final ValueChanged<Team> onTeamChanged;
  final VoidCallback onChosenChanged;

  /// The team this side's selection was already seeded from, owned by the
  /// screen so it outlives this widget.
  final String? seededTeamId;

  /// Reports the team just seeded and its real names, which only the detail
  /// fetch knows — the summary list can lag behind it.
  final void Function(String teamId, Map<String, String> namesById) onSeeded;

  const _TeamSquadPicker({
    required this.label,
    required this.teams,
    required this.selected,
    required this.chosen,
    required this.onTeamChanged,
    required this.onChosenChanged,
    required this.seededTeamId,
    required this.onSeeded,
  });

  @override
  ConsumerState<_TeamSquadPicker> createState() => _TeamSquadPickerState();
}

class _TeamSquadPickerState extends ConsumerState<_TeamSquadPicker> {
  @override
  Widget build(BuildContext context) {
    final label = widget.label;
    final teams = widget.teams;
    final selected = widget.selected;
    final chosen = widget.chosen;
    final onTeamChanged = widget.onTeamChanged;
    final onChosenChanged = widget.onChosenChanged;
    final detail = ref.watch(teamProvider(selected.id));

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(child: Text(label, style: context.texts.titleSmall)),
              Text(
                '${chosen.length} picked',
                style: context.texts.labelSmall
                    ?.copyWith(color: context.cric.faint),
              ),
            ],
          ),
          const SizedBox(height: 10),
          DropdownButtonFormField<String>(
            initialValue: selected.id,
            isExpanded: true,
            decoration: const InputDecoration(isDense: true),
            items: [
              for (final t in teams)
                DropdownMenuItem(value: t.id, child: Text(t.name)),
            ],
            onChanged: (v) {
              if (v == null) return;
              onTeamChanged(teams.firstWhere((t) => t.id == v));
            },
          ),
          const SizedBox(height: 8),
          detail.when(
            loading: () => const SkeletonBox(height: 60),
            error: (e, _) => Text(
              'Could not load the squad.',
              style: context.texts.bodySmall,
            ),
            data: (team) {
              // Default to the whole squad the first time this team loads, and
              // hand the real names up so the match carries them rather than
              // the ids from the possibly-stale summary list.
              //
              // The marker is recorded even for an empty roster: without that,
              // switching to an empty team and back would look unseeded and
              // wipe a squad the scorer had already trimmed.
              if (widget.seededTeamId != team.id) {
                final members = team.members;
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  if (!mounted) return;
                  chosen
                    ..clear()
                    ..addAll(members.map((m) => m.playerId));
                  widget.onSeeded(
                    team.id,
                    {for (final m in members) m.playerId: m.name},
                  );
                  onChosenChanged();
                });
              }

              if (team.members.isEmpty) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Text(
                    'This team has no players yet.',
                    style: context.texts.bodySmall,
                  ),
                );
              }
              return Column(
                children: [
                  for (final m in team.members)
                    CheckboxListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      controlAffinity: ListTileControlAffinity.leading,
                      value: chosen.contains(m.playerId),
                      onChanged: (v) {
                        if (v == true) {
                          chosen.add(m.playerId);
                        } else {
                          chosen.remove(m.playerId);
                        }
                        onChosenChanged();
                      },
                      title: Text(
                        '${m.name}${m.isCaptain ? ' (c)' : ''}',
                        style: context.texts.bodyMedium,
                      ),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
