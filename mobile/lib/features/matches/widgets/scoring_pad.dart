import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/models/match.dart';
import '../../../core/models/rules.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/common.dart';
import 'capture_dialogs.dart';

/// The ball-by-ball input surface.
///
/// Nothing here computes a score. Each tap assembles a [BallRequest], the
/// server folds it into the event log, and the whole state comes back.
class ScoringPad extends StatefulWidget {
  final MatchState match;
  final Innings innings;

  /// Sends one delivery. Throws on rejection so the pad can surface the
  /// engine's own message.
  final Future<void> Function(BallRequest ball) onBall;
  final Future<void> Function(String bowler) onSetBowler;
  final Future<void> Function() onUndo;

  const ScoringPad({
    super.key,
    required this.match,
    required this.innings,
    required this.onBall,
    required this.onSetBowler,
    required this.onUndo,
  });

  @override
  State<ScoringPad> createState() => _ScoringPadState();
}

class _ScoringPadState extends State<ScoringPad> {
  static const _trackShotsKey = 'cn_track_shots';
  static const _trackPitchKey = 'cn_track_pitch';

  bool _trackShots = false;
  bool _trackPitch = false;
  bool _busy = false;
  SharedPreferences? _prefs;

  @override
  void initState() {
    super.initState();
    _loadPrefs();
  }

  Future<void> _loadPrefs() async {
    try {
      final p = await SharedPreferences.getInstance();
      if (!mounted) return;
      setState(() {
        _prefs = p;
        _trackShots = p.getBool(_trackShotsKey) ?? false;
        _trackPitch = p.getBool(_trackPitchKey) ?? false;
      });
    } catch (_) {
      // Tracking simply stays off.
    }
  }

  MatchRules get _rules => widget.match.rules;

  /// Assemble the delivery, then chain the optional capture prompts.
  Future<void> _capture(BallRequest base) async {
    if (_busy) return;
    var ball = base;

    if (_trackShots && ball.isBatShot) {
      final wagon = await showWagonCapture(context);
      if (!mounted) return;
      if (wagon != null) {
        ball = ball.copyWith(wagonX: wagon.x, wagonY: wagon.y);
      }
    }

    if (_trackPitch) {
      final pitch = await showPitchCapture(context);
      if (!mounted) return;
      if (pitch != null) {
        ball = ball.copyWith(pitchX: pitch.x, pitchY: pitch.y);
      }
    }

    await _send(ball);
  }

  Future<void> _send(BallRequest ball) async {
    setState(() => _busy = true);
    try {
      HapticFeedback.selectionClick();
      await widget.onBall(ball);
    } catch (e) {
      if (!mounted) return;
      // A 409 is the engine refusing an illegal delivery. Show what it said.
      context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _runs(int n) => _capture(
        BallRequest(action: BallRequest.actionRuns, value: n),
      );

  Future<void> _extra(String action) async {
    // A dialog is only worth showing when the engine will actually keep the
    // runs. A no-ball's value maps to runs off the bat, so byes-off-a-no-ball
    // are unreachable through the API and asking for them would lose them.
    final needsRuns = switch (action) {
      BallRequest.actionWide => _rules.wide.allowByes,
      BallRequest.actionNoBall => _rules.noBall.offBatCounts,
      _ => true,
    };

    if (!needsRuns) {
      await _capture(BallRequest(action: action));
      return;
    }

    final runs = await showExtraRunsDialog(context, action: action);
    if (runs == null || !mounted) return;
    await _capture(BallRequest(action: action, value: runs));
  }

  Future<void> _wicket() async {
    final choice = await showWicketDialog(
      context,
      rules: _rules,
      innings: widget.innings,
      fielders: fieldingSideNames(widget.match),
    );
    if (choice == null || !mounted) return;
    await _capture(BallRequest(
      action: BallRequest.actionWicket,
      dismissal: choice.dismissal,
      batterOut: choice.batterOut,
      fielder: choice.fielder,
      // Runs completed before the dismissal still count.
      value: choice.runs,
    ));
  }

  /// In a rule-out format, clearing the boundary on the full is a dismissal.
  Future<void> _boundaryOut() => _capture(const BallRequest(
        action: BallRequest.actionWicket,
        dismissal: Dismissals.boundaryOut,
      ));

  /// A free hit protects the batter from everything except run out, obstruction
  /// and hitting twice, so boundary-out cannot apply. The engine drops such a
  /// dismissal silently, which would look like a lost six to the scorer.
  bool get _boundaryOutAvailable =>
      _rules.overBoundaryOut && !widget.innings.freeHit;

  Future<void> _undo() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await widget.onUndo();
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _toggle(String key, bool value) async {
    setState(() {
      if (key == _trackShotsKey) {
        _trackShots = value;
      } else {
        _trackPitch = value;
      }
    });
    await _prefs?.setBool(key, value);
  }

  @override
  Widget build(BuildContext context) {
    // Between overs the server waits for a bowler before it accepts a ball.
    final needsBowler = widget.match.overPending || widget.match.awaitingBowler;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (needsBowler)
          _BowlerPicker(
            bowlers: widget.match.availableBowlers,
            staged: widget.match.stagedBowler,
            busy: _busy,
            onPick: (name) async {
              setState(() => _busy = true);
              try {
                await widget.onSetBowler(name);
              } catch (e) {
                if (context.mounted) context.toastError(e);
              } finally {
                if (mounted) setState(() => _busy = false);
              }
            },
          ),

        // The pad appears once a bowler is staged, so a wrong pick can still be
        // corrected before the first legal delivery.
        if (!widget.match.awaitingBowler || widget.match.stagedBowler != null)
          Padding(
            padding: EdgeInsets.only(top: needsBowler ? 12 : 0),
            child: _pad(context),
          ),
      ],
    );
  }

  Widget _pad(BuildContext context) {
    final bowler = widget.match.stagedBowler ?? widget.innings.bowler;

    return CnCard(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  bowler == null ? 'Scoring' : 'Bowling: $bowler',
                  style: context.texts.labelLarge
                      ?.copyWith(color: context.cric.muted),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              _TrackToggle(
                label: 'Shots',
                icon: Icons.my_location,
                value: _trackShots,
                onChanged: (v) => _toggle(_trackShotsKey, v),
              ),
              const SizedBox(width: 6),
              _TrackToggle(
                label: 'Pitch',
                icon: Icons.grid_on,
                value: _trackPitch,
                onChanged: (v) => _toggle(_trackPitchKey, v),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Runs off the bat.
          Row(
            children: [
              for (final n in [0, 1, 2, 3])
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: PadButton(
                      label: '$n',
                      onTap: _busy ? null : () => _runs(n),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: PadButton(
                    label: '4',
                    color: context.cric.four,
                    onTap: _busy ? null : () => _runs(4),
                  ),
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: _boundaryOutAvailable
                      ? PadButton(
                          label: '6 = OUT',
                          color: context.cric.wicket,
                          fontSize: 15,
                          onTap: _busy ? null : _boundaryOut,
                        )
                      : PadButton(
                          label: '6',
                          color: context.cric.six,
                          onTap: _busy ? null : () => _runs(6),
                        ),
                ),
              ),
              Expanded(
                flex: 2,
                child: PadButton(
                  label: 'OUT',
                  color: context.cric.wicket,
                  filled: true,
                  fontSize: 17,
                  onTap: _busy ? null : _wicket,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Extras — only the ones this rulebook allows.
          Row(
            children: [
              if (_rules.wide.enabled)
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: PadButton(
                      label: 'Wd',
                      color: context.cric.amber,
                      fontSize: 15,
                      onTap: _busy
                          ? null
                          : () => _extra(BallRequest.actionWide),
                    ),
                  ),
                ),
              if (_rules.noBall.enabled)
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: PadButton(
                      label: 'Nb',
                      color: context.cric.amber,
                      fontSize: 15,
                      onTap: _busy
                          ? null
                          : () => _extra(BallRequest.actionNoBall),
                    ),
                  ),
                ),
              if (_rules.byesAllowed)
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: PadButton(
                      label: 'B',
                      color: context.cric.amber,
                      fontSize: 15,
                      onTap:
                          _busy ? null : () => _extra(BallRequest.actionBye),
                    ),
                  ),
                ),
              if (_rules.legByesAllowed)
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: PadButton(
                      label: 'Lb',
                      color: context.cric.amber,
                      fontSize: 15,
                      onTap: _busy
                          ? null
                          : () => _extra(BallRequest.actionLegBye),
                    ),
                  ),
                ),
              Expanded(
                child: PadButton(
                  label: 'Undo',
                  icon: Icons.undo,
                  fontSize: 13,
                  onTap: _busy ? null : _undo,
                ),
              ),
            ],
          ),

          if (_busy) ...[
            const SizedBox(height: 10),
            const LinearProgressIndicator(minHeight: 2),
          ],
        ],
      ),
    );
  }
}

/// One key on the pad. Large enough to hit reliably at the ground.
class PadButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final VoidCallback? onTap;
  final Color? color;
  final bool filled;
  final double fontSize;

  const PadButton({
    super.key,
    required this.label,
    this.icon,
    this.onTap,
    this.color,
    this.filled = false,
    this.fontSize = 20,
  });

  @override
  Widget build(BuildContext context) {
    final c = color ?? context.scheme.onSurface;
    final bg = filled ? c : c.withValues(alpha: 0.10);
    final fg = filled ? Colors.white : c;
    final disabled = onTap == null;

    return Opacity(
      opacity: disabled ? 0.45 : 1,
      child: Material(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            height: 56,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: c.withValues(alpha: filled ? 1 : 0.3)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (icon != null) ...[
                  Icon(icon, size: 15, color: fg),
                  const SizedBox(width: 4),
                ],
                Flexible(
                  child: Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.texts.titleMedium?.copyWith(
                      color: fg,
                      fontSize: fontSize,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TrackToggle extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _TrackToggle({
    required this.label,
    required this.icon,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final c = value ? context.scheme.primary : context.cric.faint;
    return InkWell(
      onTap: () => onChanged(!value),
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
          color: value ? context.cric.accentSoft : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: value ? c : context.cric.line),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 12, color: c),
            const SizedBox(width: 4),
            Text(
              label,
              style: context.texts.labelSmall
                  ?.copyWith(color: c, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }
}

/// Choose who bowls the next over. The previous over's bowler is already
/// excluded server-side when consecutive overs are disallowed.
class _BowlerPicker extends StatefulWidget {
  final List<String> bowlers;
  final String? staged;
  final bool busy;
  final Future<void> Function(String bowler) onPick;

  const _BowlerPicker({
    required this.bowlers,
    required this.staged,
    required this.busy,
    required this.onPick,
  });

  @override
  State<_BowlerPicker> createState() => _BowlerPickerState();
}

class _BowlerPickerState extends State<_BowlerPicker> {
  String? _selected;

  @override
  Widget build(BuildContext context) {
    final options = widget.bowlers;
    final value = _selected ?? widget.staged ??
        (options.isNotEmpty ? options.first : null);

    return CnCard(
      color: context.cric.accentSoft,
      borderColor: context.scheme.primary.withValues(alpha: 0.3),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            widget.staged == null
                ? 'New over — pick the bowler'
                : 'Bowler (change before the first ball)',
            style: context.texts.titleSmall,
          ),
          const SizedBox(height: 10),
          if (options.isEmpty)
            Text(
              'No eligible bowlers. Check the over limits in the rulebook.',
              style: context.texts.bodySmall,
            )
          else
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: value,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      isDense: true,
                      contentPadding:
                          EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                    ),
                    items: [
                      for (final b in options)
                        DropdownMenuItem(value: b, child: Text(b)),
                    ],
                    onChanged: (v) => setState(() => _selected = v),
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: widget.busy || value == null
                      ? null
                      : () => widget.onPick(value),
                  child: Text(widget.staged == null ? 'Start over' : 'Change'),
                ),
              ],
            ),
        ],
      ),
    );
  }
}
