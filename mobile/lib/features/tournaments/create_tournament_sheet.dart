import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/tournament.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../rules/rule_providers.dart';
import '../teams/team_providers.dart';

/// Set up a competition: pick the shape, the teams and the match rules.
class CreateTournamentSheet extends ConsumerStatefulWidget {
  const CreateTournamentSheet({super.key});

  @override
  ConsumerState<CreateTournamentSheet> createState() =>
      _CreateTournamentSheetState();
}

class _CreateTournamentSheetState
    extends ConsumerState<CreateTournamentSheet> {
  final _name = TextEditingController();
  final _selected = <String>{};

  String _format = TournamentFormats.roundRobin;
  String _formatChoice = 't20';
  int _numGroups = 2;
  int _advancePerGroup = 2;
  int _winPoints = 2;
  int _tiePoints = 1;
  int _nrPoints = 1;
  bool _dls = false;
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final name = _name.text.trim();
    if (name.isEmpty) {
      context.toast('Name the tournament');
      return;
    }
    if (_selected.length < 2) {
      context.toast('Pick at least two teams');
      return;
    }

    setState(() => _busy = true);
    try {
      final api = ref.read(apiProvider);
      // A saved rulebook ships whole; a preset only needs its id.
      var formatId = 't20';
      var rules = _formatChoice.startsWith('template:') ? null : null;
      if (_formatChoice.startsWith('template:')) {
        final template = await api
            .ruleTemplate(_formatChoice.substring('template:'.length));
        rules = template.rules;
      } else {
        formatId = _formatChoice;
      }

      final created = await api.createTournament(
        name: name,
        format: _format,
        teamIds: _selected.toList(),
        formatId: formatId,
        rules: rules,
        numGroups: _numGroups,
        advancePerGroup: _advancePerGroup,
        winPoints: _winPoints,
        tiePoints: _tiePoints,
        nrPoints: _nrPoints,
        dlsEnabled: _dls,
      );
      if (!mounted) return;
      Navigator.pop(context, created);
    } catch (e) {
      if (!mounted) return;
      context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final teams = ref.watch(teamsProvider);
    final presets = ref.watch(presetsProvider);
    final templates = ref.watch(ruleTemplatesProvider);

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.9,
      builder: (context, controller) => ListView(
        controller: controller,
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 8,
          bottom: MediaQuery.of(context).viewInsets.bottom + 24,
        ),
        children: [
          Text('New tournament', style: context.texts.titleMedium),
          const SizedBox(height: 16),
          TextField(
            controller: _name,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(
              labelText: 'Tournament name',
              isDense: true,
            ),
          ),
          const SizedBox(height: 18),
          Text('Format', style: context.texts.labelLarge),
          const SizedBox(height: 8),
          CnSegmented<String>(
            selected: _format,
            onChanged: (v) => setState(() => _format = v),
            options: [
              for (final f in TournamentFormats.all)
                (value: f, label: TournamentFormats.label(f)),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            TournamentFormats.blurb(_format),
            style: context.texts.labelSmall?.copyWith(color: context.cric.faint),
          ),
          if (_format == TournamentFormats.groups) ...[
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _Stepper(
                    label: 'Groups',
                    value: _numGroups,
                    min: 2,
                    max: 16,
                    onChanged: (v) => setState(() => _numGroups = v),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _Stepper(
                    label: 'Advance per group',
                    value: _advancePerGroup,
                    min: 1,
                    max: 8,
                    onChanged: (v) => setState(() => _advancePerGroup = v),
                  ),
                ),
              ],
            ),
          ],
          if (_format != TournamentFormats.knockout) ...[
            const SizedBox(height: 16),
            Text('Points', style: context.texts.labelLarge),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _Stepper(
                    label: 'Win',
                    value: _winPoints,
                    min: 0,
                    max: 20,
                    onChanged: (v) => setState(() => _winPoints = v),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _Stepper(
                    label: 'Tie',
                    value: _tiePoints,
                    min: 0,
                    max: 20,
                    onChanged: (v) => setState(() => _tiePoints = v),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _Stepper(
                    label: 'No result',
                    value: _nrPoints,
                    min: 0,
                    max: 20,
                    onChanged: (v) => setState(() => _nrPoints = v),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 16),
          Text('Match rules', style: context.texts.labelLarge),
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
                      child: Text(t.name, overflow: TextOverflow.ellipsis),
                    ),
                ],
                orElse: () => const <DropdownMenuItem<String>>[],
              ),
            ],
            onChanged: (v) => setState(() => _formatChoice = v ?? _formatChoice),
          ),
          const SizedBox(height: 10),
          SwitchListTile(
            value: _dls,
            onChanged: (v) => setState(() => _dls = v),
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text('Rain rules (DLS)', style: context.texts.bodyMedium),
            subtitle: Text(
              'Revised targets when overs are lost',
              style: context.texts.labelSmall,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Teams (${_selected.length} picked)',
            style: context.texts.labelLarge,
          ),
          const SizedBox(height: 8),
          teams.when(
            loading: () => const SkeletonBox(height: 80),
            error: (e, _) => ErrorState(error: e),
            data: (list) {
              if (list.isEmpty) {
                return const EmptyState(
                  icon: Icons.groups_outlined,
                  title: 'No teams yet',
                  message: 'Create teams first, then run a tournament.',
                );
              }
              return Column(
                children: [
                  for (final t in list)
                    CheckboxListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      controlAffinity: ListTileControlAffinity.leading,
                      value: _selected.contains(t.id),
                      onChanged: (v) => setState(() {
                        if (v == true) {
                          _selected.add(t.id);
                        } else {
                          _selected.remove(t.id);
                        }
                      }),
                      title: Text(t.name, style: context.texts.bodyMedium),
                      subtitle:
                          Text(t.subtitle, style: context.texts.labelSmall),
                    ),
                ],
              );
            },
          ),
          const SizedBox(height: 18),
          ElevatedButton(
            onPressed: _busy ? null : _create,
            child: Text(_busy ? 'Creating' : 'Create tournament'),
          ),
        ],
      ),
    );
  }
}

class _Stepper extends StatelessWidget {
  final String label;
  final int value;
  final int min;
  final int max;
  final ValueChanged<int> onChanged;

  const _Stepper({
    required this.label,
    required this.value,
    required this.min,
    required this.max,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: context.texts.labelSmall),
        const SizedBox(height: 2),
        Container(
          decoration: BoxDecoration(
            color: context.cric.surfaceVariant,
            borderRadius: BorderRadius.circular(9),
            border: Border.all(color: context.cric.line),
          ),
          child: Row(
            children: [
              IconButton(
                iconSize: 16,
                visualDensity: VisualDensity.compact,
                onPressed: value <= min ? null : () => onChanged(value - 1),
                icon: const Icon(Icons.remove),
              ),
              Expanded(
                child: Text(
                  '$value',
                  textAlign: TextAlign.center,
                  style: context.texts.titleSmall,
                ),
              ),
              IconButton(
                iconSize: 16,
                visualDensity: VisualDensity.compact,
                onPressed: value >= max ? null : () => onChanged(value + 1),
                icon: const Icon(Icons.add),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
