import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/common.dart';

/// The calculators and match-day helpers from the website's tools page.
/// Everything here runs on the device; nothing calls the API.
class ToolsScreen extends StatelessWidget {
  const ToolsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Tools'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Calculators'),
              Tab(text: 'Toss'),
              Tab(text: 'Picker'),
            ],
          ),
        ),
        body: const TabBarView(
          children: [
            _Calculators(),
            _TossFlipper(),
            _PickerWheel(),
          ],
        ),
      ),
    );
  }
}

class _Calculators extends StatelessWidget {
  const _Calculators();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 32),
      children: [
        Text(
          'Overs go in as overs.balls, so 12.3 means twelve overs and three '
          'balls.',
          style: context.texts.bodySmall,
        ),
        const SizedBox(height: 14),
        const _RunRate(),
        const SizedBox(height: 12),
        const _RequiredRate(),
        const SizedBox(height: 12),
        const _StrikeRate(),
        const SizedBox(height: 12),
        const _Economy(),
        const SizedBox(height: 12),
        const _NetRunRate(),
      ],
    );
  }
}

/// A calculator card: a few numeric inputs and one derived answer.
class _Calc extends StatefulWidget {
  final String title;
  final List<({String key, String label})> fields;
  final ({String value, String? note}) Function(Map<String, double?>) compute;

  const _Calc({
    required this.title,
    required this.fields,
    required this.compute,
  });

  @override
  State<_Calc> createState() => _CalcState();
}

class _CalcState extends State<_Calc> {
  final _controllers = <String, TextEditingController>{};

  @override
  void initState() {
    super.initState();
    for (final f in widget.fields) {
      _controllers[f.key] = TextEditingController()
        ..addListener(() => setState(() {}));
    }
  }

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final values = <String, double?>{
      for (final e in _controllers.entries)
        e.key: double.tryParse(e.value.text.trim()),
    };
    final result = widget.compute(values);

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(widget.title, style: context.texts.titleSmall),
          const SizedBox(height: 12),
          // Two per row. Four across a 375px phone left each field ~85px, so
          // "Runs for / Overs faced / Runs against / Overs bowled" all
          // truncated to "Run… / Ove… / Run… / Ove…" and the scorer could not
          // tell their own side's boxes from the opposition's.
          for (var i = 0; i < widget.fields.length; i += 2)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                children: [
                  for (var j = i;
                      j < i + 2 && j < widget.fields.length;
                      j++) ...[
                    if (j > i) const SizedBox(width: 10),
                    Expanded(
                      child: TextField(
                        controller: _controllers[widget.fields[j].key],
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
                        decoration: InputDecoration(
                          labelText: widget.fields[j].label,
                          isDense: true,
                        ),
                      ),
                    ),
                  ],
                  // An odd last field keeps its half rather than stretching
                  // across the card away from its partner above.
                  if (widget.fields.length - i == 1) const Spacer(),
                ],
              ),
            ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: context.cric.accentSoft,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              children: [
                Text(
                  result.value,
                  style: context.texts.headlineSmall
                      ?.copyWith(color: context.scheme.primary),
                ),
                if (result.note != null) ...[
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(result.note!, style: context.texts.bodySmall),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _RunRate extends StatelessWidget {
  const _RunRate();

  @override
  Widget build(BuildContext context) => _Calc(
        title: 'Run rate',
        fields: const [
          (key: 'runs', label: 'Runs'),
          (key: 'overs', label: 'Overs'),
        ],
        compute: (v) {
          final runs = v['runs'];
          final overs = v['overs'] == null ? null : Fmt.oversToDecimal(v['overs']!);
          if (runs == null || overs == null || overs == 0) {
            return (value: '—', note: null);
          }
          return (value: (runs / overs).toStringAsFixed(2), note: 'runs per over');
        },
      );
}

class _RequiredRate extends StatelessWidget {
  const _RequiredRate();

  @override
  Widget build(BuildContext context) => _Calc(
        title: 'Required run rate',
        fields: const [
          (key: 'target', label: 'Target'),
          (key: 'score', label: 'Score'),
          (key: 'overs', label: 'Overs left'),
        ],
        compute: (v) {
          final target = v['target'];
          final score = v['score'];
          final balls =
              v['overs'] == null ? null : Fmt.oversToBalls(v['overs']!);
          if (target == null || score == null || balls == null || balls == 0) {
            return (value: '—', note: null);
          }
          final need = target - score;
          if (need <= 0) {
            return (value: 'Won', note: 'Target already passed');
          }
          return (
            value: ((need / balls) * 6).toStringAsFixed(2),
            note: 'Need ${need.round()} off $balls '
                '${balls == 1 ? 'ball' : 'balls'}',
          );
        },
      );
}

class _StrikeRate extends StatelessWidget {
  const _StrikeRate();

  @override
  Widget build(BuildContext context) => _Calc(
        title: 'Strike rate',
        fields: const [
          (key: 'runs', label: 'Runs'),
          (key: 'balls', label: 'Balls'),
        ],
        compute: (v) {
          final runs = v['runs'];
          final balls = v['balls'];
          if (runs == null || balls == null || balls == 0) {
            return (value: '—', note: null);
          }
          return (
            value: ((runs / balls) * 100).toStringAsFixed(2),
            note: 'runs per 100 balls',
          );
        },
      );
}

class _Economy extends StatelessWidget {
  const _Economy();

  @override
  Widget build(BuildContext context) => _Calc(
        title: 'Economy rate',
        fields: const [
          (key: 'runs', label: 'Runs conceded'),
          (key: 'overs', label: 'Overs'),
        ],
        compute: (v) {
          final runs = v['runs'];
          final overs =
              v['overs'] == null ? null : Fmt.oversToDecimal(v['overs']!);
          if (runs == null || overs == null || overs == 0) {
            return (value: '—', note: null);
          }
          return (
            value: (runs / overs).toStringAsFixed(2),
            note: 'runs per over',
          );
        },
      );
}

class _NetRunRate extends StatelessWidget {
  const _NetRunRate();

  @override
  Widget build(BuildContext context) => _Calc(
        title: 'Net run rate',
        fields: const [
          (key: 'rf', label: 'Runs for'),
          (key: 'of', label: 'Overs faced'),
          (key: 'ra', label: 'Runs against'),
          (key: 'oa', label: 'Overs bowled'),
        ],
        compute: (v) {
          final rf = v['rf'];
          final ra = v['ra'];
          final of = v['of'] == null ? null : Fmt.oversToDecimal(v['of']!);
          final oa = v['oa'] == null ? null : Fmt.oversToDecimal(v['oa']!);
          if (rf == null ||
              ra == null ||
              of == null ||
              oa == null ||
              of == 0 ||
              oa == 0) {
            return (value: '—', note: null);
          }
          final nrr = (rf / of) - (ra / oa);
          return (value: Fmt.signed(nrr), note: 'net run rate');
        },
      );
}

/// A coin for the toss.
class _TossFlipper extends StatefulWidget {
  const _TossFlipper();

  @override
  State<_TossFlipper> createState() => _TossFlipperState();
}

class _TossFlipperState extends State<_TossFlipper>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1300),
  );

  bool? _heads;
  bool _flipping = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _flip() async {
    if (_flipping) return;
    setState(() {
      _flipping = true;
      _heads = null;
    });
    final result = math.Random().nextBool();
    await _controller.forward(from: 0);
    if (!mounted) return;
    setState(() {
      _heads = result;
      _flipping = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedBuilder(
              animation: _controller,
              builder: (context, child) => Transform(
                alignment: Alignment.center,
                transform: Matrix4.identity()
                  ..setEntry(3, 2, 0.001)
                  ..rotateY(_controller.value * math.pi * 10),
                child: child,
              ),
              child: Container(
                width: 140,
                height: 140,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [
                      context.scheme.primary,
                      context.scheme.primary.withValues(alpha: 0.6),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: Center(
                  child: Icon(
                    Icons.sports_cricket,
                    size: 52,
                    color: context.scheme.onPrimary,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 28),
            Text(
              _flipping
                  ? 'Flipping'
                  : _heads == null
                      ? 'Tap to toss'
                      : (_heads! ? 'Heads' : 'Tails'),
              style: context.texts.headlineSmall,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _flipping ? null : _flip,
              icon: const Icon(Icons.casino_outlined, size: 19),
              label: const Text('Toss the coin'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Spin to pick a name — batting order, who fields first, anything.
class _PickerWheel extends StatefulWidget {
  const _PickerWheel();

  @override
  State<_PickerWheel> createState() => _PickerWheelState();
}

class _PickerWheelState extends State<_PickerWheel>
    with SingleTickerProviderStateMixin {
  final _input = TextEditingController();
  final _options = <String>[];

  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2600),
  );
  late Animation<double> _spin = const AlwaysStoppedAnimation(0);

  String? _winner;
  bool _spinning = false;

  @override
  void dispose() {
    _input.dispose();
    _controller.dispose();
    super.dispose();
  }

  void _add() {
    final text = _input.text.trim();
    if (text.isEmpty || _options.length >= 12) return;
    setState(() {
      _options.add(text);
      _input.clear();
      _winner = null;
    });
  }

  Future<void> _spinWheel() async {
    if (_options.length < 2 || _spinning) return;
    setState(() {
      _spinning = true;
      _winner = null;
    });

    final index = math.Random().nextInt(_options.length);
    final slice = 2 * math.pi / _options.length;
    // Several full turns, landing with the winner under the pointer at the top.
    final target = 6 * 2 * math.pi + (2 * math.pi - (index + 0.5) * slice);
    _spin = Tween<double>(begin: 0, end: target).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );
    await _controller.forward(from: 0);
    if (!mounted) return;
    setState(() {
      _winner = _options[index];
      _spinning = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 32),
      children: [
        CnCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) => _add(),
                      decoration: const InputDecoration(
                        hintText: 'Add a name',
                        isDense: true,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  ElevatedButton(
                    onPressed: _options.length >= 12 ? null : _add,
                    child: const Text('Add'),
                  ),
                ],
              ),
              if (_options.isNotEmpty) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (var i = 0; i < _options.length; i++)
                      InputChip(
                        label: Text(_options[i]),
                        onDeleted: () => setState(() {
                          _options.removeAt(i);
                          _winner = null;
                        }),
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 18),
        if (_options.length < 2)
          const EmptyState(
            icon: Icons.pie_chart_outline,
            title: 'Add at least two names',
            message: 'Then spin to pick one at random.',
          )
        else ...[
          AspectRatio(
            aspectRatio: 1,
            child: AnimatedBuilder(
              animation: _controller,
              builder: (context, _) => Stack(
                alignment: Alignment.center,
                children: [
                  Transform.rotate(
                    angle: _spin.value,
                    child: CustomPaint(
                      size: Size.infinite,
                      painter: _WheelPainter(
                        options: _options,
                        accent: context.scheme.primary,
                        line: context.cric.line,
                      ),
                    ),
                  ),
                  Positioned(
                    top: 0,
                    child: Icon(Icons.arrow_drop_down,
                        size: 40, color: context.cric.wicket),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (_winner != null)
            Center(
              child: Text(
                _winner!,
                style: context.texts.headlineSmall
                    ?.copyWith(color: context.scheme.primary),
              ),
            ),
          const SizedBox(height: 14),
          ElevatedButton.icon(
            onPressed: _spinning ? null : _spinWheel,
            icon: const Icon(Icons.refresh, size: 19),
            label: const Text('Spin'),
          ),
        ],
      ],
    );
  }
}

class _WheelPainter extends CustomPainter {
  final List<String> options;
  final Color accent;
  final Color line;

  const _WheelPainter({
    required this.options,
    required this.accent,
    required this.line,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final r = math.min(size.width, size.height) / 2 - 4;
    final centre = Offset(size.width / 2, size.height / 2);
    final slice = 2 * math.pi / options.length;

    for (var i = 0; i < options.length; i++) {
      // Alternating tints of the accent keep the wheel on-palette.
      final t = i / options.length;
      final paint = Paint()
        ..color = HSLColor.fromColor(accent)
            .withLightness((0.32 + t * 0.28).clamp(0.0, 1.0))
            .toColor();
      // Start at the top and go clockwise, matching the pointer.
      final start = -math.pi / 2 + i * slice;
      canvas.drawArc(
        Rect.fromCircle(center: centre, radius: r),
        start,
        slice,
        true,
        paint,
      );

      final mid = start + slice / 2;
      final tp = TextPainter(
        text: TextSpan(
          text: options[i],
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
        textDirection: TextDirection.ltr,
        maxLines: 1,
        ellipsis: '…',
      )..layout(maxWidth: r * 0.7);

      canvas.save();
      canvas.translate(
        centre.dx + math.cos(mid) * r * 0.6,
        centre.dy + math.sin(mid) * r * 0.6,
      );
      // Rotating with the slice puts every name in the left half upside down.
      // Flipping those through half a turn keeps the text the right way up
      // while still following the wheel.
      final upsideDown = math.cos(mid) < 0;
      canvas.rotate(upsideDown ? mid + math.pi : mid);
      tp.paint(canvas, Offset(-tp.width / 2, -tp.height / 2));
      canvas.restore();
    }

    canvas.drawCircle(
      centre,
      r,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..color = line,
    );
  }

  @override
  bool shouldRepaint(covariant _WheelPainter old) => old.options != options;
}
