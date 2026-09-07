import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/rules.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../auth/login_screen.dart';
import 'rule_providers.dart';

/// Compose a rulebook.
///
/// Every field maps one-to-one onto the server's `MatchRules`, and the whole
/// object round-trips, so nothing the engine cares about is quietly dropped.
class RuleBuilderScreen extends ConsumerStatefulWidget {
  /// `preset:<id>` or `template:<id>` to start from an existing rulebook.
  final String? templateId;

  const RuleBuilderScreen({super.key, this.templateId});

  @override
  ConsumerState<RuleBuilderScreen> createState() => _RuleBuilderScreenState();
}

class _RuleBuilderScreenState extends ConsumerState<RuleBuilderScreen> {
  MatchRules _rules = const MatchRules(
    name: 'My rulebook',
    playersPerSide: 8,
    oversPerInnings: 6,
    ballType: BallTypes.tennis,
    lastManStands: true,
    overBoundaryOut: true,
    powerplays: [
      PowerplayRange(startOver: 1, endOver: 2),
    ],
  );

  final _nameController = TextEditingController();
  bool _loading = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _nameController.text = _rules.name;
    if (widget.templateId != null) _loadSource(widget.templateId!);
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  /// Start from a preset or a saved template rather than a blank slate.
  Future<void> _loadSource(String source) async {
    setState(() => _loading = true);
    try {
      final api = ref.read(apiProvider);
      MatchRules loaded;
      if (source.startsWith('preset:')) {
        loaded = await api.preset(source.substring('preset:'.length));
        // A preset copied into the builder becomes a new custom rulebook.
        loaded = loaded.copyWith(
          name: '${loaded.name} (my version)',
          formatId: 'custom',
        );
      } else {
        final template = await api.ruleTemplate(
          source.substring('template:'.length),
        );
        loaded = template.rules;
      }
      if (!mounted) return;
      setState(() {
        _rules = loaded;
        _nameController.text = loaded.name;
      });
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _update(MatchRules Function(MatchRules) change) =>
      setState(() => _rules = change(_rules));

  Future<void> _save() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      context.toast('Name your rulebook');
      return;
    }
    // The server rejects a powerplay that runs past the innings, so catch it
    // here and say so plainly instead of surfacing a validation array.
    for (final pp in _rules.powerplays) {
      if (pp.endOver > _rules.oversPerInnings) {
        context.toast('A powerplay runs past the end of the innings');
        return;
      }
      if (pp.endOver < pp.startOver) {
        context.toast('A powerplay ends before it starts');
        return;
      }
    }
    if (_rules.maxOversPerBowler != null &&
        _rules.maxOversPerBowler! > _rules.oversPerInnings) {
      context.toast('Overs per bowler cannot exceed the innings length');
      return;
    }

    setState(() => _saving = true);
    try {
      await ref.read(apiProvider).saveRuleTemplate(
            _rules.copyWith(name: name, formatId: 'custom'),
          );
      ref.invalidate(ruleTemplatesProvider);
      if (!mounted) return;
      context.toast('Rulebook saved');
      context.pop();
    } catch (e) {
      if (!mounted) return;
      context.toastError(e);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    if (!auth.can(Caps.manageRules)) {
      return Scaffold(
        appBar: AppBar(title: const Text('Rule builder')),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: GateCard(
            what: 'build rule templates',
            signedIn: auth.isSignedIn,
            role: auth.user?.role,
            onSignIn: () => context.push(Routes.login),
            onRegister: () => context.push(Routes.register),
          ),
        ),
      );
    }

    if (_loading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Rule builder')),
        body: const Padding(
          padding: EdgeInsets.all(16),
          child: ListSkeleton(rows: 4),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Rule builder')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          _preview(),
          const SizedBox(height: 14),
          _shapeCard(),
          const SizedBox(height: 14),
          _extrasCard(),
          const SizedBox(height: 14),
          _fieldingCard(),
          const SizedBox(height: 14),
          _formatQuirksCard(),
          const SizedBox(height: 14),
          _dismissalsCard(),
          const SizedBox(height: 22),
          ElevatedButton.icon(
            onPressed: _saving ? null : _save,
            icon: _saving
                ? const ButtonSpinner()
                : const Icon(Icons.save_outlined, size: 19),
            label: const Text('Save rulebook'),
          ),
        ],
      ),
    );
  }

  Widget _preview() {
    final r = _rules;
    final chips = <String>[
      if (r.lastManStands) 'Last man stands',
      if (r.overBoundaryOut) 'Rule-out',
      if (r.noBall.freeHit) 'Free hit',
      if (r.wide.enabled) 'Wides count',
      if (r.byesAllowed) 'Byes',
      if (r.legByesAllowed) 'Leg byes',
      if (r.allowedDismissals.contains(Dismissals.lbw)) 'LBW',
      if (r.superOverOnTie) 'Super over',
      if (r.dlsEnabled) 'DLS',
      if (r.allowDeclaration) 'Declarations',
    ];

    return CnCard(
      color: context.cric.accentSoft,
      borderColor: context.scheme.primary.withValues(alpha: 0.25),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _nameController,
            style: context.texts.titleMedium,
            decoration: const InputDecoration(
              labelText: 'Rulebook name',
              isDense: true,
              filled: false,
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              contentPadding: EdgeInsets.zero,
            ),
          ),
          const SizedBox(height: 6),
          Text(_rules.summaryLine, style: context.texts.bodySmall),
          const SizedBox(height: 12),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              if (chips.isEmpty)
                Text('No extra rules', style: context.texts.bodySmall)
              else
                for (final c in chips) CnBadge(text: c),
            ],
          ),
        ],
      ),
    );
  }

  Widget _shapeCard() {
    return _Section(
      title: 'Shape of the contest',
      children: [
        _NumberRow(
          label: 'Players per side',
          value: _rules.playersPerSide,
          min: 2,
          max: 20,
          onChanged: (v) => _update((r) => r.copyWith(playersPerSide: v)),
        ),
        _NumberRow(
          label: 'Overs per innings',
          value: _rules.oversPerInnings,
          min: 1,
          max: 200,
          onChanged: (v) => _update((r) => r.copyWith(oversPerInnings: v)),
        ),
        _NumberRow(
          label: 'Balls per over',
          value: _rules.ballsPerOver,
          min: 1,
          max: 12,
          onChanged: (v) => _update((r) => r.copyWith(ballsPerOver: v)),
        ),
        _NumberRow(
          label: 'Max overs per bowler',
          value: _rules.maxOversPerBowler,
          min: 1,
          max: _rules.oversPerInnings,
          nullable: true,
          nullLabel: 'Any',
          onChanged: (v) => _update(
            (r) => v == null
                ? r.copyWith(clearMaxOversPerBowler: true)
                : r.copyWith(maxOversPerBowler: v),
          ),
        ),
        const SizedBox(height: 6),
        Text('Ball type', style: context.texts.labelLarge),
        const SizedBox(height: 8),
        CnSegmented<String>(
          selected: _rules.ballType,
          onChanged: (v) => _update((r) => r.copyWith(ballType: v)),
          options: [
            for (final b in BallTypes.all)
              (value: b, label: BallTypes.label(b)),
          ],
        ),
        const SizedBox(height: 14),
        Text('Boundary rule', style: context.texts.labelLarge),
        const SizedBox(height: 8),
        CnSegmented<bool>(
          selected: _rules.overBoundaryOut,
          onChanged: (v) => _update((r) => r.copyWith(overBoundaryOut: v)),
          options: const [
            (value: false, label: 'Full ground'),
            (value: true, label: 'Rule-out'),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          _rules.overBoundaryOut
              ? 'Clearing the boundary on the full is OUT, not six. Common in '
                  'box and gully cricket where space is tight.'
              : 'Sixes count normally.',
          style: context.texts.labelSmall?.copyWith(color: context.cric.faint),
        ),
        _ToggleRow(
          label: 'Bowlers may bowl consecutive overs',
          value: _rules.allowConsecutiveOvers,
          onChanged: (v) => _update((r) => r.copyWith(allowConsecutiveOvers: v)),
        ),
      ],
    );
  }

  Widget _extrasCard() {
    return _Section(
      title: 'Extras',
      children: [
        _ToggleRow(
          label: 'Wides',
          subtitle: 'A wide concedes runs and is re-bowled by default',
          value: _rules.wide.enabled,
          onChanged: (v) => _update(
            (r) => r.copyWith(wide: r.wide.copyWith(enabled: v)),
          ),
        ),
        if (_rules.wide.enabled) ...[
          _NumberRow(
            label: 'Wide penalty',
            value: _rules.wide.runPenalty,
            min: 0,
            max: 5,
            indent: true,
            onChanged: (v) => _update(
              (r) => r.copyWith(wide: r.wide.copyWith(runPenalty: v ?? 1)),
            ),
          ),
          _ToggleRow(
            label: 'Wide counts as a legal ball',
            subtitle: 'Off means the delivery is re-bowled',
            indent: true,
            value: _rules.wide.countsAsLegalBall,
            onChanged: (v) => _update(
              (r) => r.copyWith(wide: r.wide.copyWith(countsAsLegalBall: v)),
            ),
          ),
          _ToggleRow(
            label: 'Batters may run on a wide',
            indent: true,
            value: _rules.wide.allowByes,
            onChanged: (v) => _update(
              (r) => r.copyWith(wide: r.wide.copyWith(allowByes: v)),
            ),
          ),
        ],
        const Divider(height: 24),
        _ToggleRow(
          label: 'No-balls',
          value: _rules.noBall.enabled,
          onChanged: (v) => _update(
            (r) => r.copyWith(noBall: r.noBall.copyWith(enabled: v)),
          ),
        ),
        if (_rules.noBall.enabled) ...[
          _NumberRow(
            label: 'No-ball penalty',
            value: _rules.noBall.runPenalty,
            min: 0,
            max: 5,
            indent: true,
            onChanged: (v) => _update(
              (r) => r.copyWith(noBall: r.noBall.copyWith(runPenalty: v ?? 1)),
            ),
          ),
          _ToggleRow(
            label: 'Free hit after a no-ball',
            indent: true,
            value: _rules.noBall.freeHit,
            onChanged: (v) => _update(
              (r) => r.copyWith(noBall: r.noBall.copyWith(freeHit: v)),
            ),
          ),
          _ToggleRow(
            label: 'Runs off a no-ball go to the batter',
            indent: true,
            value: _rules.noBall.offBatCounts,
            onChanged: (v) => _update(
              (r) => r.copyWith(noBall: r.noBall.copyWith(offBatCounts: v)),
            ),
          ),
          _ToggleRow(
            label: 'No-ball counts as a legal ball',
            indent: true,
            value: _rules.noBall.countsAsLegalBall,
            onChanged: (v) => _update(
              (r) =>
                  r.copyWith(noBall: r.noBall.copyWith(countsAsLegalBall: v)),
            ),
          ),
        ],
        const Divider(height: 24),
        _ToggleRow(
          label: 'Byes',
          value: _rules.byesAllowed,
          onChanged: (v) => _update((r) => r.copyWith(byesAllowed: v)),
        ),
        _ToggleRow(
          label: 'Leg byes',
          value: _rules.legByesAllowed,
          onChanged: (v) => _update((r) => r.copyWith(legByesAllowed: v)),
        ),
      ],
    );
  }

  Widget _fieldingCard() {
    return _Section(
      title: 'Fielding restrictions',
      children: [
        _NumberRow(
          label: 'Fielders outside the circle (normal overs)',
          value: _rules.defaultFieldersOutside,
          min: 0,
          max: 20,
          onChanged: (v) =>
              _update((r) => r.copyWith(defaultFieldersOutside: v ?? 5)),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: Text('Powerplays', style: context.texts.labelLarge),
            ),
            TextButton.icon(
              onPressed: () => _update(
                (r) => r.copyWith(
                  powerplays: [
                    ...r.powerplays,
                    PowerplayRange(
                      startOver: r.powerplays.isEmpty
                          ? 1
                          : r.powerplays.last.endOver + 1,
                      endOver: r.powerplays.isEmpty
                          ? 2
                          : r.powerplays.last.endOver + 2,
                    ),
                  ],
                ),
              ),
              icon: const Icon(Icons.add, size: 17),
              label: const Text('Add'),
            ),
          ],
        ),
        if (_rules.powerplays.isEmpty)
          Text('No powerplays.', style: context.texts.bodySmall)
        else
          for (var i = 0; i < _rules.powerplays.length; i++)
            _PowerplayRow(
              range: _rules.powerplays[i],
              maxOver: _rules.oversPerInnings,
              onChanged: (updated) => _update((r) {
                final list = [...r.powerplays];
                list[i] = updated;
                return r.copyWith(powerplays: list);
              }),
              onRemove: () => _update((r) {
                final list = [...r.powerplays]..removeAt(i);
                return r.copyWith(powerplays: list);
              }),
            ),
      ],
    );
  }

  Widget _formatQuirksCard() {
    return _Section(
      title: 'Format quirks',
      children: [
        _ToggleRow(
          label: 'Last man stands',
          subtitle: 'The final batter carries on alone',
          value: _rules.lastManStands,
          onChanged: (v) => _update((r) => r.copyWith(lastManStands: v)),
        ),
        _ToggleRow(
          label: 'Super over breaks a tie',
          value: _rules.superOverOnTie,
          onChanged: (v) => _update((r) => r.copyWith(superOverOnTie: v)),
        ),
        _ToggleRow(
          label: 'Allow declarations',
          subtitle: 'The captain may close the innings early',
          value: _rules.allowDeclaration,
          onChanged: (v) => _update((r) => r.copyWith(allowDeclaration: v)),
        ),
        _ToggleRow(
          label: 'Rain rules (DLS)',
          subtitle: 'Revised targets when overs are lost',
          value: _rules.dlsEnabled,
          onChanged: (v) => _update((r) => r.copyWith(dlsEnabled: v)),
        ),
        if (_rules.dlsEnabled) ...[
          _NumberRow(
            label: 'Minimum overs for a DLS result',
            subtitle: '0 derives it from the innings length',
            value: _rules.dlsMinOvers,
            min: 0,
            max: _rules.oversPerInnings,
            indent: true,
            onChanged: (v) => _update((r) => r.copyWith(dlsMinOvers: v ?? 0)),
          ),
        ],
        const Divider(height: 24),
        _NumberRow(
          label: 'Runs for a boundary four',
          value: _rules.fourValue,
          min: 1,
          max: 10,
          onChanged: (v) => _update((r) => r.copyWith(fourValue: v ?? 4)),
        ),
        _NumberRow(
          label: 'Runs for a six',
          value: _rules.sixValue,
          min: 1,
          max: 12,
          onChanged: (v) => _update((r) => r.copyWith(sixValue: v ?? 6)),
        ),
      ],
    );
  }

  Widget _dismissalsCard() {
    return _Section(
      title: 'Dismissals allowed',
      subtitle: 'Turn off anything your format does not play, such as LBW in '
          'gully cricket.',
      children: [
        for (final d in Dismissals.standard)
          _ToggleRow(
            label: Dismissals.label(d),
            value: _rules.allowedDismissals.contains(d),
            onChanged: (v) => _update((r) {
              final list = [...r.allowedDismissals];
              if (v) {
                if (!list.contains(d)) list.add(d);
              } else {
                list.remove(d);
              }
              return r.copyWith(allowedDismissals: list);
            }),
          ),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final String? subtitle;
  final List<Widget> children;

  const _Section({
    required this.title,
    this.subtitle,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(title, style: context.texts.titleSmall),
          if (subtitle != null) ...[
            const SizedBox(height: 4),
            Text(subtitle!, style: context.texts.bodySmall),
          ],
          const SizedBox(height: 8),
          ...children,
        ],
      ),
    );
  }
}

class _ToggleRow extends StatelessWidget {
  final String label;
  final String? subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;
  final bool indent;

  const _ToggleRow({
    required this.label,
    this.subtitle,
    required this.value,
    required this.onChanged,
    this.indent = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(left: indent ? 14 : 0),
      child: SwitchListTile(
        value: value,
        onChanged: onChanged,
        dense: true,
        contentPadding: EdgeInsets.zero,
        title: Text(label, style: context.texts.bodyMedium),
        subtitle: subtitle == null
            ? null
            : Text(subtitle!, style: context.texts.labelSmall),
      ),
    );
  }
}

class _NumberRow extends StatelessWidget {
  final String label;
  final String? subtitle;
  final int? value;
  final int min;
  final int max;
  final bool nullable;
  final String nullLabel;
  final bool indent;
  final ValueChanged<int?> onChanged;

  const _NumberRow({
    required this.label,
    this.subtitle,
    required this.value,
    required this.min,
    required this.max,
    this.nullable = false,
    this.nullLabel = 'None',
    this.indent = false,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final current = value;

    return Padding(
      padding: EdgeInsets.fromLTRB(indent ? 14 : 0, 8, 0, 8),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: context.texts.bodyMedium),
                if (subtitle != null)
                  Text(subtitle!, style: context.texts.labelSmall),
              ],
            ),
          ),
          IconButton(
            iconSize: 19,
            visualDensity: VisualDensity.compact,
            onPressed: current == null || current <= min
                ? (nullable && current == null ? null : null)
                : () => onChanged(current - 1),
            icon: const Icon(Icons.remove_circle_outline),
          ),
          SizedBox(
            width: 46,
            child: Text(
              current?.toString() ?? nullLabel,
              textAlign: TextAlign.center,
              style: context.texts.titleSmall,
            ),
          ),
          IconButton(
            iconSize: 19,
            visualDensity: VisualDensity.compact,
            onPressed: current != null && current >= max
                ? null
                : () => onChanged(current == null ? min : current + 1),
            icon: const Icon(Icons.add_circle_outline),
          ),
          if (nullable)
            IconButton(
              iconSize: 17,
              visualDensity: VisualDensity.compact,
              tooltip: 'Clear',
              onPressed: current == null ? null : () => onChanged(null),
              icon: const Icon(Icons.close),
            ),
        ],
      ),
    );
  }
}

class _PowerplayRow extends StatelessWidget {
  final PowerplayRange range;
  final int maxOver;
  final ValueChanged<PowerplayRange> onChanged;
  final VoidCallback onRemove;

  const _PowerplayRow({
    required this.range,
    required this.maxOver,
    required this.onChanged,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    final invalid = range.endOver > maxOver || range.endOver < range.startOver;

    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.fromLTRB(12, 10, 6, 10),
      decoration: BoxDecoration(
        color: context.cric.surfaceVariant,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: invalid ? context.cric.wicket : context.cric.line,
        ),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  initialValue: range.label,
                  decoration: const InputDecoration(
                    labelText: 'Label',
                    isDense: true,
                  ),
                  onChanged: (v) => onChanged(range.copyWith(label: v)),
                ),
              ),
              IconButton(
                iconSize: 18,
                icon: const Icon(Icons.close),
                onPressed: onRemove,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _MiniNumber(
                  label: 'From over',
                  value: range.startOver,
                  min: 1,
                  max: maxOver,
                  onChanged: (v) => onChanged(range.copyWith(startOver: v)),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _MiniNumber(
                  label: 'To over',
                  value: range.endOver,
                  min: 1,
                  max: maxOver,
                  onChanged: (v) => onChanged(range.copyWith(endOver: v)),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _MiniNumber(
                  label: 'Fielders out',
                  value: range.maxFieldersOutside,
                  min: 0,
                  max: 11,
                  onChanged: (v) =>
                      onChanged(range.copyWith(maxFieldersOutside: v)),
                ),
              ),
            ],
          ),
          if (invalid) ...[
            const SizedBox(height: 6),
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'This range does not fit inside the innings.',
                style: context.texts.labelSmall
                    ?.copyWith(color: context.cric.wicket),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _MiniNumber extends StatelessWidget {
  final String label;
  final int value;
  final int min;
  final int max;
  final ValueChanged<int> onChanged;

  const _MiniNumber({
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
        Row(
          children: [
            InkWell(
              onTap: value <= min ? null : () => onChanged(value - 1),
              child: Icon(Icons.remove, size: 16, color: context.cric.muted),
            ),
            Expanded(
              child: Text(
                '$value',
                textAlign: TextAlign.center,
                style: context.texts.titleSmall,
              ),
            ),
            InkWell(
              onTap: value >= max ? null : () => onChanged(value + 1),
              child: Icon(Icons.add, size: 16, color: context.cric.muted),
            ),
          ],
        ),
      ],
    );
  }
}
