import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/auth/auth_provider.dart';
import '../../../core/models/match.dart';
import '../../../core/models/rules.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/common.dart';
import '../match_providers.dart';

/// Rain, bad light and the revised target.
///
/// The scorer only flags the stoppage and confirms the new total overs; the
/// server computes the Duckworth-Lewis-Stern target, par score and resources.
class DlsPanel extends ConsumerStatefulWidget {
  final String matchId;
  final DlsState dls;
  final Innings innings;
  final MatchController controller;

  const DlsPanel({
    super.key,
    required this.matchId,
    required this.dls,
    required this.innings,
    required this.controller,
  });

  @override
  ConsumerState<DlsPanel> createState() => _DlsPanelState();
}

class _DlsPanelState extends ConsumerState<DlsPanel> {
  final _oversController = TextEditingController();
  String _reason = 'rain';
  bool _busy = false;

  @override
  void dispose() {
    _oversController.dispose();
    super.dispose();
  }

  Future<void> _run(Future<MatchState> Function() action) async {
    setState(() => _busy = true);
    try {
      await widget.controller.act(action);
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String get _nowHhMm {
    final now = DateTime.now();
    return '${now.hour.toString().padLeft(2, '0')}:'
        '${now.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final api = ref.read(apiProvider);
    final d = widget.dls;

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(Icons.umbrella_outlined, size: 18, color: context.cric.four),
              const SizedBox(width: 8),
              Text('Rain & revised target', style: context.texts.titleSmall),
            ],
          ),
          if (d.hasSummary) ...[
            const SizedBox(height: 14),
            DlsSummaryGrid(dls: d, innings: widget.innings),
          ],
          if (d.interruptions.isNotEmpty) ...[
            const SizedBox(height: 12),
            for (final i in d.interruptions)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  children: [
                    Icon(Icons.circle, size: 6, color: context.cric.faint),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${StoppageReasons.label(i.reason)} · innings ${i.innings}',
                        style: context.texts.bodySmall,
                      ),
                    ),
                    Text(
                      i.pending
                          ? 'in progress'
                          : '-${i.oversLost.toStringAsFixed(i.oversLost == i.oversLost.roundToDouble() ? 0 : 1)} ov',
                      style: context.texts.labelSmall?.copyWith(
                        color:
                            i.pending ? context.cric.amber : context.cric.faint,
                      ),
                    ),
                  ],
                ),
              ),
          ],
          const SizedBox(height: 14),
          if (d.pending) ..._resumeControls(api) else ..._idleControls(api),
          const SizedBox(height: 10),
          Text(
            'You only confirm the overs. The revised target, par score and '
            'required rate compute themselves.',
            style: context.texts.labelSmall?.copyWith(color: context.cric.faint),
          ),
        ],
      ),
    );
  }

  List<Widget> _idleControls(dynamic api) => [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          decoration: BoxDecoration(
            color: context.cric.surfaceVariant,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: context.cric.line),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: _reason,
              isExpanded: true,
              items: [
                for (final r in StoppageReasons.all)
                  DropdownMenuItem(
                      value: r, child: Text(StoppageReasons.label(r))),
              ],
              onChanged: (v) => setState(() => _reason = v ?? _reason),
            ),
          ),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: ElevatedButton.icon(
                onPressed: _busy
                    ? null
                    : () => _run(() => api.interruptMatch(
                          widget.matchId,
                          _reason,
                          at: _nowHhMm,
                        )),
                icon: const Icon(Icons.pause_circle_outline, size: 18),
                label: const Text('Interrupt'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                    foregroundColor: context.cric.wicket),
                onPressed: _busy
                    ? null
                    : () async {
                        final ok = await confirmDialog(
                          context,
                          title: 'Abandon the match?',
                          message:
                              'If the chase has passed the minimum overs it is '
                              'decided on DLS par. Otherwise it is a no result.',
                          confirmLabel: 'Abandon',
                        );
                        if (ok) {
                          await _run(
                              () => api.abandonMatch(widget.matchId, _reason));
                        }
                      },
                icon: const Icon(Icons.cancel_outlined, size: 18),
                label: const Text('Abandon'),
              ),
            ),
          ],
        ),
      ];

  List<Widget> _resumeControls(dynamic api) => [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: context.cric.amberSoft,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: context.cric.amber.withValues(alpha: 0.3)),
          ),
          child: Row(
            children: [
              Icon(Icons.pause_circle_filled,
                  size: 18, color: context.cric.amber),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Play interrupted. Confirm the new total overs to resume.',
                  style: context.texts.bodySmall,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _oversController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: 'New total overs for this innings',
            isDense: true,
          ),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: _busy
                    ? null
                    : () => _run(() => api.cancelInterruption(widget.matchId)),
                child: const Text('False alarm'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: ElevatedButton(
                onPressed: _busy
                    ? null
                    : () {
                        final overs =
                            int.tryParse(_oversController.text.trim());
                        if (overs == null || overs < 1) {
                          context.toast(
                              'Enter the new total overs for this innings');
                          return;
                        }
                        if (overs > 50) {
                          context.toast('A revised innings cannot exceed 50 overs');
                          return;
                        }
                        _run(() => api.resumeMatch(
                              widget.matchId,
                              overs,
                              at: _nowHhMm,
                            ));
                      },
                child: const Text('Resume play'),
              ),
            ),
          ],
        ),
      ];
}

/// The read-only revision summary, for viewers who are not scoring.
class DlsSummary extends StatelessWidget {
  final DlsState dls;
  final Innings innings;

  const DlsSummary({super.key, required this.dls, required this.innings});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.umbrella_outlined, size: 18, color: context.cric.four),
              const SizedBox(width: 8),
              Text('Revised target', style: context.texts.titleSmall),
            ],
          ),
          const SizedBox(height: 14),
          DlsSummaryGrid(dls: dls, innings: innings),
        ],
      ),
    );
  }
}

class DlsSummaryGrid extends StatelessWidget {
  final DlsState dls;
  final Innings innings;

  const DlsSummaryGrid({super.key, required this.dls, required this.innings});

  @override
  Widget build(BuildContext context) {
    final stats = <({String label, String value})>[
      (label: 'Original overs', value: '${dls.originalOvers}'),
      if (dls.revisedOvers != null)
        (label: 'Revised overs', value: '${dls.revisedOvers}'),
      if (dls.revisedTarget != null)
        (label: 'Target', value: '${dls.revisedTarget}'),
      if (dls.par != null) (label: 'Par now', value: '${dls.par}'),
      (label: 'Score', value: innings.scoreLine),
      (label: 'Overs lost', value: dls.oversLost.toStringAsFixed(1)),
    ];

    // Ahead or behind par is the number that actually decides a rain result.
    String? parNote;
    Color? parColor;
    if (dls.par != null) {
      final delta = innings.runs - dls.par!;
      if (delta > 0) {
        parNote = '$delta ahead of par';
        parColor = context.scheme.primary;
      } else if (delta < 0) {
        parNote = '${-delta} behind par';
        parColor = context.cric.wicket;
      } else {
        parNote = 'Level with par';
        parColor = context.cric.amber;
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        StatGrid(stats: stats, columns: 3),
        if (parNote != null) ...[
          const SizedBox(height: 12),
          Text(
            parNote,
            style: context.texts.bodyMedium
                ?.copyWith(color: parColor, fontWeight: FontWeight.w700),
          ),
        ],
        if (dls.abandoned) ...[
          const SizedBox(height: 10),
          CnBadge(
            text: 'Abandoned'
                '${dls.abandonReason == null ? '' : ' · ${StoppageReasons.label(dls.abandonReason!)}'}',
            color: context.cric.wicket,
          ),
        ],
        const SizedBox(height: 10),
        Text(
          'Duckworth-Lewis-Stern · resources ${dls.r1.toStringAsFixed(1)}% '
          'v ${dls.r2.toStringAsFixed(1)}%',
          style: context.texts.labelSmall?.copyWith(color: context.cric.faint),
        ),
      ],
    );
  }
}
