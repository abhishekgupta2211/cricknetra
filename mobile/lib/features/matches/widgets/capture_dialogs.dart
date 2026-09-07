import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../core/models/match.dart';
import '../../../core/models/rules.dart';
import '../../../core/theme/app_theme.dart';

/// What the scorer chose in the wicket dialog.
///
/// `runs` is what the batters completed before the dismissal — the pair often
/// cross on a run out, and those runs count.
typedef WicketChoice = ({
  String dismissal,
  String batterOut,
  String? fielder,
  int runs,
});

/// Ask how the batter was out.
///
/// `batterOut` must be the literal `striker` or `non_striker` — the server
/// validates that pattern, so a player name here is a guaranteed 422.
Future<WicketChoice?> showWicketDialog(
  BuildContext context, {
  required MatchRules rules,
  required Innings innings,
  required List<String> fielders,

  /// Whether the delivery in question is a free hit. Defaults to the innings'
  /// flag, which describes the NEXT ball — correct while scoring, wrong when
  /// correcting an earlier delivery, so that caller passes it explicitly.
  bool? freeHit,
}) {
  return showDialog<WicketChoice>(
    context: context,
    builder: (context) => _WicketDialog(
      rules: rules,
      innings: innings,
      fielders: fielders,
      freeHit: freeHit ?? innings.freeHit,
    ),
  );
}

class _WicketDialog extends StatefulWidget {
  final MatchRules rules;
  final Innings innings;
  final List<String> fielders;
  final bool freeHit;

  const _WicketDialog({
    required this.rules,
    required this.innings,
    required this.fielders,
    required this.freeHit,
  });

  @override
  State<_WicketDialog> createState() => _WicketDialogState();
}

class _WicketDialogState extends State<_WicketDialog> {
  late String _dismissal;
  String _batterOut = 'striker';
  String? _fielder;
  int _runs = 0;

  @override
  void initState() {
    super.initState();
    final options = _options;
    _dismissal = options.isEmpty ? Dismissals.bowled : options.first;
  }

  /// On a free hit only run-out, obstruction and hitting twice are possible.
  List<String> get _options {
    final all = widget.rules.selectableDismissals
        .where((d) => d != Dismissals.boundaryOut)
        .toList();
    if (!widget.freeHit) return all;
    return all.where(Dismissals.onFreeHit.contains).toList();
  }

  bool get _wantsFielder => Dismissals.needsFielder.contains(_dismissal);

  /// Runs only make sense where the ball stayed live.
  bool get _wantsRuns => Dismissals.canCompleteRuns.contains(_dismissal);

  @override
  Widget build(BuildContext context) {
    final striker = widget.innings.striker ?? 'Striker';
    final nonStriker = widget.innings.nonStriker ?? 'Non-striker';

    final noneAvailable = _options.isEmpty;

    return AlertDialog(
      title: const Text('Wicket'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (noneAvailable)
              Text(
                'No dismissal is possible on this delivery under these rules.',
                style: context.texts.bodySmall
                    ?.copyWith(color: context.cric.wicket),
              ),
            if (widget.freeHit)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  'Free hit — only a run out, obstruction or hitting the ball '
                  'twice can dismiss the batter.',
                  style: context.texts.bodySmall
                      ?.copyWith(color: context.cric.amber),
                ),
              ),
            DropdownButtonFormField<String>(
              initialValue: _dismissal,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'How out'),
              items: [
                for (final d in _options)
                  DropdownMenuItem(value: d, child: Text(Dismissals.label(d))),
              ],
              onChanged: (v) => setState(() {
                _dismissal = v ?? _dismissal;
                // A bowled or caught ends the ball, so any runs already
                // picked would be credited to the batter in error.
                if (!_wantsRuns) _runs = 0;
              }),
            ),
            const SizedBox(height: 14),
            Text('Who is out', style: context.texts.labelLarge),
            const SizedBox(height: 6),
            SegmentedButton<String>(
              segments: [
                ButtonSegment(
                  value: 'striker',
                  label: Text(striker, overflow: TextOverflow.ellipsis),
                ),
                ButtonSegment(
                  value: 'non_striker',
                  label: Text(nonStriker, overflow: TextOverflow.ellipsis),
                ),
              ],
              selected: {_batterOut},
              showSelectedIcon: false,
              onSelectionChanged: (s) => setState(() => _batterOut = s.first),
            ),
            if (_wantsFielder) ...[
              const SizedBox(height: 14),
              DropdownButtonFormField<String?>(
                initialValue: _fielder,
                isExpanded: true,
                decoration: const InputDecoration(
                  labelText: 'Fielder (optional)',
                ),
                items: [
                  const DropdownMenuItem<String?>(
                    value: null,
                    child: Text('—'),
                  ),
                  for (final f in widget.fielders)
                    DropdownMenuItem<String?>(value: f, child: Text(f)),
                ],
                onChanged: (v) => setState(() => _fielder = v),
              ),
            ],
            if (_wantsRuns) ...[
              const SizedBox(height: 14),
              Text('Runs completed', style: context.texts.labelLarge),
              const SizedBox(height: 2),
              Text(
                'What the batters ran before the dismissal.',
                style: context.texts.labelSmall,
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  for (final n in [0, 1, 2, 3])
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: _RunChoice(
                          value: n,
                          selected: _runs == n,
                          onTap: () => setState(() => _runs = n),
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: context.cric.wicket,
            foregroundColor: Colors.white,
          ),
          onPressed: noneAvailable
              ? null
              : () => Navigator.pop(context, (
                    dismissal: _dismissal,
                    batterOut: _batterOut,
                    fielder: _fielder,
                    runs: _runs,
                  )),
          child: const Text('Out'),
        ),
      ],
    );
  }
}

class _RunChoice extends StatelessWidget {
  final int value;
  final bool selected;
  final VoidCallback onTap;

  const _RunChoice({
    required this.value,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(9),
      child: Container(
        height: 42,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? context.cric.accentSoft : Colors.transparent,
          borderRadius: BorderRadius.circular(9),
          border: Border.all(
            color: selected ? context.scheme.primary : context.cric.line,
          ),
        ),
        child: Text(
          '$value',
          style: context.texts.titleSmall?.copyWith(
            color: selected ? context.scheme.primary : null,
          ),
        ),
      ),
    );
  }
}

/// How many runs came off a wide, no-ball, bye or leg-bye.
///
/// The engine adds the wide/no-ball penalty itself, so this only captures what
/// the batters actually ran or hit.
Future<int?> showExtraRunsDialog(
  BuildContext context, {
  required String action,
}) {
  final ({String title, String hint, List<int> runs}) config = switch (action) {
    BallRequest.actionNoBall => (
        title: 'No-ball',
        hint: 'Runs off the bat. The penalty is added automatically.',
        runs: [0, 1, 2, 3, 4, 6],
      ),
    BallRequest.actionWide => (
        title: 'Wide',
        hint: 'Extra runs the batters ran. The penalty is added automatically.',
        runs: [0, 1, 2, 3, 4],
      ),
    BallRequest.actionBye => (
        title: 'Byes',
        hint: 'Runs run off a delivery the batter did not touch.',
        runs: [1, 2, 3, 4],
      ),
    _ => (
        title: 'Leg byes',
        hint: 'Runs off the pad or body.',
        runs: [1, 2, 3, 4],
      ),
  };

  return showDialog<int>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(config.title),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(config.hint, style: context.texts.bodySmall),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              for (final r in config.runs)
                SizedBox(
                  width: 62,
                  height: 52,
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context, r),
                    child: Text('$r', style: context.texts.titleMedium),
                  ),
                ),
            ],
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
      ],
    ),
  );
}

/// Where the shot went, as unit coordinates for the wagon wheel.
Future<({double x, double y})?> showWagonCapture(BuildContext context) {
  return showDialog<({double x, double y})>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('Where did it go?'),
      contentPadding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      content: SizedBox(
        width: 280,
        height: 300,
        child: Column(
          children: [
            Text(
              'Tap the field in the direction of the shot.',
              style: context.texts.bodySmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            Expanded(
              child: _FieldPicker(
                onPick: (x, y) => Navigator.pop(context, (x: x, y: y)),
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Skip direction'),
        ),
      ],
    ),
  );
}

/// A cricket field the scorer taps to record shot direction.
class _FieldPicker extends StatelessWidget {
  final void Function(double x, double y) onPick;

  const _FieldPicker({required this.onPick});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final size = math.min(constraints.maxWidth, constraints.maxHeight);
        return Center(
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTapUp: (details) {
              final r = size / 2;
              // Screen y grows downward; "straight" is up the ground, so the
              // vertical axis is inverted to match the server's convention.
              var x = (details.localPosition.dx - r) / r;
              var y = (r - details.localPosition.dy) / r;
              final mag = math.sqrt(x * x + y * y);
              if (mag > 1) {
                x /= mag;
                y /= mag;
              }
              onPick(
                double.parse(x.clamp(-1.0, 1.0).toStringAsFixed(3)),
                double.parse(y.clamp(-1.0, 1.0).toStringAsFixed(3)),
              );
            },
            child: CustomPaint(
              size: Size(size, size),
              painter: _FieldPainter(
                line: context.cric.line,
                grass: context.cric.surfaceVariant,
                accent: context.scheme.primary,
                label: context.cric.faint,
              ),
            ),
          ),
        );
      },
    );
  }
}

class _FieldPainter extends CustomPainter {
  final Color line;
  final Color grass;
  final Color accent;
  final Color label;

  const _FieldPainter({
    required this.line,
    required this.grass,
    required this.accent,
    required this.label,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final r = size.width / 2;
    final centre = Offset(r, r);

    canvas.drawCircle(centre, r - 1, Paint()..color = grass);
    canvas.drawCircle(
      centre,
      r - 1,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5
        ..color = line,
    );
    // The 30-yard circle.
    canvas.drawCircle(
      centre,
      r * 0.52,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = line,
    );
    // The pitch, with the batter at the striker's end facing up the ground.
    final pitch = Rect.fromCenter(
      center: centre,
      width: r * 0.16,
      height: r * 0.52,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(pitch, const Radius.circular(3)),
      Paint()..color = label.withValues(alpha: 0.25),
    );
    canvas.drawCircle(
      Offset(r, r + r * 0.18),
      4,
      Paint()..color = accent,
    );

    final tp = TextPainter(
      text: TextSpan(
        text: 'straight',
        style: TextStyle(color: label, fontSize: 10, letterSpacing: 0.5),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, Offset(r - tp.width / 2, 6));
  }

  @override
  bool shouldRepaint(covariant _FieldPainter old) =>
      old.line != line || old.grass != grass || old.accent != accent;
}

/// Where the ball pitched: line across the stumps and length down the wicket.
Future<({double x, double y})?> showPitchCapture(BuildContext context) {
  return showDialog<({double x, double y})>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('Where did it pitch?'),
      contentPadding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      content: SizedBox(
        width: 260,
        height: 320,
        child: Column(
          children: [
            Text(
              'Tap the spot on the pitch.',
              style: context.texts.bodySmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            Expanded(
              child: _PitchPicker(
                onPick: (x, y) => Navigator.pop(context, (x: x, y: y)),
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Skip pitch'),
        ),
      ],
    ),
  );
}

class _PitchPicker extends StatelessWidget {
  final void Function(double x, double y) onPick;

  const _PitchPicker({required this.onPick});

  /// Length bands from the batter's end down the wicket.
  static const bands = <String>[
    'Bouncer',
    'Short',
    'Back',
    'Good',
    'Full',
    'Yorker',
  ];

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final w = math.min(constraints.maxWidth, 200.0);
        final h = constraints.maxHeight;
        return Center(
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTapUp: (d) {
              // x: -1 down leg to +1 wide outside off.
              // y: 0 at the batter (yorker) to 1 at the bowler (bouncer).
              final x = ((d.localPosition.dx - w / 2) / (w / 2)).clamp(-1.0, 1.0);
              final y = (1 - d.localPosition.dy / h).clamp(0.0, 1.0);
              onPick(
                double.parse(x.toStringAsFixed(3)),
                double.parse(y.toStringAsFixed(3)),
              );
            },
            child: CustomPaint(
              size: Size(w, h),
              painter: _PitchPainter(
                line: context.cric.line,
                strip: context.cric.surfaceVariant,
                label: context.cric.faint,
                accent: context.scheme.primary,
              ),
            ),
          ),
        );
      },
    );
  }
}

class _PitchPainter extends CustomPainter {
  final Color line;
  final Color strip;
  final Color label;
  final Color accent;

  const _PitchPainter({
    required this.line,
    required this.strip,
    required this.label,
    required this.accent,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(0, 0, size.width, size.height);
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(8)),
      Paint()..color = strip,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(8)),
      Paint()
        ..style = PaintingStyle.stroke
        ..color = line,
    );

    // Six length bands, labelled bouncer at the top down to yorker.
    final bandHeight = size.height / _PitchPicker.bands.length;
    for (var i = 0; i < _PitchPicker.bands.length; i++) {
      final y = bandHeight * (i + 1);
      if (i < _PitchPicker.bands.length - 1) {
        canvas.drawLine(
          Offset(0, y),
          Offset(size.width, y),
          Paint()
            ..color = line
            ..strokeWidth = 0.8,
        );
      }
      final tp = TextPainter(
        text: TextSpan(
          text: _PitchPicker.bands[i],
          style: TextStyle(color: label, fontSize: 9),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(5, y - bandHeight / 2 - tp.height / 2));
    }

    // Stumps at the batter's end.
    final stumpPaint = Paint()
      ..color = accent
      ..strokeWidth = 2;
    for (var i = -1; i <= 1; i++) {
      final x = size.width / 2 + i * 7;
      canvas.drawLine(
        Offset(x, size.height - 16),
        Offset(x, size.height - 2),
        stumpPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _PitchPainter old) =>
      old.line != line || old.strip != strip || old.accent != accent;
}
