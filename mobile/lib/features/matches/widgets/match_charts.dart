import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../../../core/models/match.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/common.dart';

/// Runs per over, with wickets marked and powerplay overs shaded.
class ManhattanChart extends StatelessWidget {
  final Innings innings;

  const ManhattanChart({super.key, required this.innings});

  @override
  Widget build(BuildContext context) {
    if (innings.manhattan.isEmpty) {
      return const EmptyState(
        icon: Icons.bar_chart_outlined,
        title: 'No overs bowled yet',
        message: 'Runs per over appear here as the match is scored.',
      );
    }

    // Wickets that fell in each over, so the bar can carry a marker.
    final wicketsByOver = <int, int>{};
    for (final f in innings.fallOfWickets) {
      final over = double.tryParse(f.over)?.floor() ?? 0;
      wicketsByOver[over] = (wicketsByOver[over] ?? 0) + 1;
    }

    final maxRuns = innings.manhattan.reduce(math.max).toDouble();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 220,
          child: LayoutBuilder(
            builder: (context, box) {
              // A fixed bar width turns a two-over innings into a pair of
              // hairlines lost in a wide chart. Give each over its share of the
              // plot, capped so a long innings does not become a solid block.
              final plot = math.max(box.maxWidth - 30, 60.0);
              final slot = plot / innings.manhattan.length;
              final barWidth = (slot * 0.55).clamp(5.0, 34.0);
              return BarChart(
            BarChartData(
              alignment: BarChartAlignment.spaceAround,
              maxY: (maxRuns * 1.25).clamp(6, double.infinity),
              barTouchData: BarTouchData(
                touchTooltipData: BarTouchTooltipData(
                  getTooltipColor: (_) => context.cric.surfaceVariant,
                  getTooltipItem: (group, _, rod, _) {
                    final over = group.x + 1;
                    final w = wicketsByOver[group.x] ?? 0;
                    return BarTooltipItem(
                      'Over $over: ${rod.toY.toInt()} run'
                      '${rod.toY == 1 ? '' : 's'}'
                      '${w > 0 ? ', $w wkt' : ''}',
                      context.texts.labelSmall ?? const TextStyle(),
                    );
                  },
                ),
              ),
              titlesData: FlTitlesData(
                topTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 30,
                    interval: _yInterval(maxRuns),
                    getTitlesWidget: (v, _) => Text(
                      v.toInt().toString(),
                      style: context.texts.labelSmall
                          ?.copyWith(color: context.cric.faint),
                    ),
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 24,
                    getTitlesWidget: (v, _) {
                      final over = v.toInt() + 1;
                      // Thin the labels out so they never collide.
                      final step = innings.manhattan.length > 20 ? 5 : 2;
                      if (over % step != 0 && over != 1) {
                        return const SizedBox.shrink();
                      }
                      return Text(
                        '$over',
                        style: context.texts.labelSmall
                            ?.copyWith(color: context.cric.faint),
                      );
                    },
                  ),
                ),
              ),
              gridData: FlGridData(
                drawVerticalLine: false,
                horizontalInterval: _yInterval(maxRuns),
                getDrawingHorizontalLine: (_) =>
                    FlLine(color: context.cric.line, strokeWidth: 1),
              ),
              borderData: FlBorderData(show: false),
              barGroups: [
                for (var i = 0; i < innings.manhattan.length; i++)
                  BarChartGroupData(
                    x: i,
                    barRods: [
                      BarChartRodData(
                        toY: innings.manhattan[i].toDouble(),
                        width: barWidth,
                        borderRadius: BorderRadius.circular(3),
                        color: (wicketsByOver[i] ?? 0) > 0
                            ? context.cric.wicket
                            : context.scheme.primary,
                      ),
                    ],
                  ),
              ],
            ),
          );
            },
          ),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            _Legend(color: context.scheme.primary, label: 'Runs per over'),
            const SizedBox(width: 16),
            _Legend(color: context.cric.wicket, label: 'Over with a wicket'),
          ],
        ),
      ],
    );
  }

  static double _yInterval(double maxRuns) {
    if (maxRuns <= 10) return 2;
    if (maxRuns <= 25) return 5;
    return 10;
  }
}

/// Cumulative runs for both innings, with wickets marked on the line.
class WormChart extends StatelessWidget {
  final List<Innings> innings;

  const WormChart({super.key, required this.innings});

  @override
  Widget build(BuildContext context) {
    final sides = innings.where((i) => i.worm.isNotEmpty).take(2).toList();
    if (sides.isEmpty) {
      return const EmptyState(
        icon: Icons.show_chart,
        title: 'Nothing to plot yet',
        message: 'The run chase appears here once overs are bowled.',
      );
    }

    final colors = [context.scheme.primary, context.cric.four];
    var maxRuns = 0;
    var maxOvers = 0;
    for (final s in sides) {
      if (s.worm.isNotEmpty && s.worm.last > maxRuns) maxRuns = s.worm.last;
      if (s.worm.length > maxOvers) maxOvers = s.worm.length;
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 220,
          child: LineChart(
            LineChartData(
              minX: 0,
              maxX: maxOvers.toDouble(),
              minY: 0,
              maxY: (maxRuns * 1.15).clamp(10, double.infinity),
              lineTouchData: LineTouchData(
                touchTooltipData: LineTouchTooltipData(
                  getTooltipColor: (_) => context.cric.surfaceVariant,
                  getTooltipItems: (spots) => spots
                      .map(
                        (s) => LineTooltipItem(
                          '${sides[s.barIndex].battingTeam} '
                          '${s.y.toInt()} after ${s.x.toInt()} ov',
                          context.texts.labelSmall ?? const TextStyle(),
                        ),
                      )
                      .toList(),
                ),
              ),
              titlesData: FlTitlesData(
                topTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 34,
                    getTitlesWidget: (v, _) => Text(
                      v.toInt().toString(),
                      style: context.texts.labelSmall
                          ?.copyWith(color: context.cric.faint),
                    ),
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 24,
                    interval: maxOvers > 20 ? 5 : 2,
                    getTitlesWidget: (v, _) => Text(
                      v.toInt().toString(),
                      style: context.texts.labelSmall
                          ?.copyWith(color: context.cric.faint),
                    ),
                  ),
                ),
              ),
              gridData: FlGridData(
                drawVerticalLine: false,
                getDrawingHorizontalLine: (_) =>
                    FlLine(color: context.cric.line, strokeWidth: 1),
              ),
              borderData: FlBorderData(show: false),
              lineBarsData: [
                for (var s = 0; s < sides.length; s++)
                  LineChartBarData(
                    isCurved: true,
                    curveSmoothness: 0.22,
                    color: colors[s % colors.length],
                    barWidth: 2.6,
                    dotData: FlDotData(
                      // Mark the exact over each wicket fell.
                      show: true,
                      checkToShowDot: (spot, _) =>
                          _wicketOvers(sides[s]).contains(spot.x.toInt()),
                      getDotPainter: (_, _, _, _) => FlDotCirclePainter(
                        radius: 3.4,
                        color: context.cric.wicket,
                        strokeWidth: 0,
                      ),
                    ),
                    belowBarData: BarAreaData(
                      show: true,
                      color: colors[s % colors.length].withValues(alpha: 0.10),
                    ),
                    spots: [
                      const FlSpot(0, 0),
                      for (var i = 0; i < sides[s].worm.length; i++)
                        FlSpot((i + 1).toDouble(), sides[s].worm[i].toDouble()),
                    ],
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 16,
          runSpacing: 6,
          children: [
            for (var s = 0; s < sides.length; s++)
              _Legend(
                color: colors[s % colors.length],
                label: sides[s].battingTeam,
              ),
            _Legend(color: context.cric.wicket, label: 'Wicket'),
          ],
        ),
      ],
    );
  }

  static Set<int> _wicketOvers(Innings innings) => innings.fallOfWickets
      .map((f) => (double.tryParse(f.over)?.ceil() ?? 0))
      .toSet();
}

/// Where every scoring shot went.
class WagonWheel extends StatelessWidget {
  final List<WagonPoint> shots;

  /// Show only this batter's shots when set.
  final String? batterFilter;

  const WagonWheel({super.key, required this.shots, this.batterFilter});

  @override
  Widget build(BuildContext context) {
    final points = batterFilter == null
        ? shots
        : shots.where((s) => s.batter == batterFilter).toList();

    if (points.isEmpty) {
      return const EmptyState(
        icon: Icons.my_location,
        title: 'No shot directions recorded',
        message: 'Turn on Shots while scoring to plot the wagon wheel.',
      );
    }

    return Column(
      children: [
        AspectRatio(
          aspectRatio: 1,
          child: CustomPaint(
            painter: _WagonPainter(
              shots: points,
              line: context.cric.line,
              grass: context.cric.surfaceVariant,
              faint: context.cric.faint,
              one: context.scheme.onSurface,
              four: context.cric.four,
              six: context.cric.six,
              wicket: context.cric.wicket,
            ),
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 14,
          runSpacing: 6,
          alignment: WrapAlignment.center,
          children: [
            _Legend(color: context.scheme.onSurface, label: '1-3'),
            _Legend(color: context.cric.four, label: 'Four'),
            _Legend(color: context.cric.six, label: 'Six'),
            _Legend(color: context.cric.wicket, label: 'Wicket'),
          ],
        ),
      ],
    );
  }
}

class _WagonPainter extends CustomPainter {
  final List<WagonPoint> shots;
  final Color line;
  final Color grass;
  final Color faint;
  final Color one;
  final Color four;
  final Color six;
  final Color wicket;

  const _WagonPainter({
    required this.shots,
    required this.line,
    required this.grass,
    required this.faint,
    required this.one,
    required this.four,
    required this.six,
    required this.wicket,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final r = math.min(size.width, size.height) / 2;
    final centre = Offset(size.width / 2, size.height / 2);

    canvas.drawCircle(centre, r - 2, Paint()..color = grass);
    canvas.drawCircle(
      centre,
      r - 2,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5
        ..color = line,
    );
    canvas.drawCircle(
      centre,
      r * 0.52,
      Paint()
        ..style = PaintingStyle.stroke
        ..color = line,
    );

    // The pitch, with the batter facing up the ground.
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromCenter(
            center: centre, width: r * 0.14, height: r * 0.48),
        const Radius.circular(3),
      ),
      Paint()..color = faint.withValues(alpha: 0.22),
    );

    for (final s in shots) {
      // The server's y grows toward the straight boundary; screen y grows down.
      final end = Offset(centre.dx + s.x * r, centre.dy - s.y * r);
      final color = s.wicket
          ? wicket
          : s.runs >= 6
              ? six
              : s.runs >= 4
                  ? four
                  : one;
      canvas.drawLine(
        centre,
        end,
        Paint()
          ..color = color.withValues(alpha: 0.7)
          ..strokeWidth = s.runs >= 4 ? 2 : 1.3
          ..strokeCap = StrokeCap.round,
      );
      canvas.drawCircle(end, s.runs >= 4 ? 3.4 : 2.4, Paint()..color = color);
    }
  }

  @override
  bool shouldRepaint(covariant _WagonPainter old) => old.shots != shots;
}

/// Where each delivery pitched, coloured by outcome.
class PitchMap extends StatelessWidget {
  final List<PitchMark> marks;
  final String? bowlerFilter;

  const PitchMap({super.key, required this.marks, this.bowlerFilter});

  @override
  Widget build(BuildContext context) {
    final points = bowlerFilter == null
        ? marks
        : marks.where((m) => m.bowler == bowlerFilter).toList();

    if (points.isEmpty) {
      return const EmptyState(
        icon: Icons.grid_on,
        title: 'No pitch data recorded',
        message: 'Turn on Pitch while scoring to build the pitch map.',
      );
    }

    return Column(
      children: [
        AspectRatio(
          aspectRatio: 0.62,
          child: CustomPaint(
            painter: _PitchMapPainter(
              marks: points,
              line: context.cric.line,
              strip: context.cric.surfaceVariant,
              faint: context.cric.faint,
              dot: context.scheme.onSurface,
              four: context.cric.four,
              six: context.cric.six,
              wicket: context.cric.wicket,
            ),
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 14,
          runSpacing: 6,
          alignment: WrapAlignment.center,
          children: [
            _Legend(color: context.scheme.onSurface, label: 'Runs'),
            _Legend(color: context.cric.four, label: 'Four'),
            _Legend(color: context.cric.six, label: 'Six'),
            _Legend(color: context.cric.wicket, label: 'Wicket'),
          ],
        ),
      ],
    );
  }
}

class _PitchMapPainter extends CustomPainter {
  final List<PitchMark> marks;
  final Color line;
  final Color strip;
  final Color faint;
  final Color dot;
  final Color four;
  final Color six;
  final Color wicket;

  static const _bands = <String>[
    'Bouncer',
    'Short',
    'Back of length',
    'Good length',
    'Full',
    'Yorker',
  ];

  const _PitchMapPainter({
    required this.marks,
    required this.line,
    required this.strip,
    required this.faint,
    required this.dot,
    required this.four,
    required this.six,
    required this.wicket,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(0, 0, size.width, size.height);
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(10)),
      Paint()..color = strip,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(10)),
      Paint()
        ..style = PaintingStyle.stroke
        ..color = line,
    );

    final bandHeight = size.height / _bands.length;
    for (var i = 0; i < _bands.length; i++) {
      final y = bandHeight * (i + 1);
      if (i < _bands.length - 1) {
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
          text: _bands[i],
          style: TextStyle(color: faint, fontSize: 9),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(6, y - bandHeight / 2 - tp.height / 2));
    }

    for (final m in marks) {
      final x = size.width / 2 + m.x * (size.width / 2);
      final y = size.height * (1 - m.y);
      final color = m.wicket
          ? wicket
          : m.runs >= 6
              ? six
              : m.runs >= 4
                  ? four
                  : dot;
      canvas.drawCircle(
        Offset(x, y),
        m.wicket ? 5 : 3.6,
        Paint()..color = color.withValues(alpha: 0.85),
      );
    }

    // Stumps at the batter's end.
    final stumpPaint = Paint()
      ..color = faint
      ..strokeWidth = 2;
    for (var i = -1; i <= 1; i++) {
      final x = size.width / 2 + i * 7;
      canvas.drawLine(
        Offset(x, size.height - 18),
        Offset(x, size.height - 4),
        stumpPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _PitchMapPainter old) => old.marks != marks;
}

class _Legend extends StatelessWidget {
  final Color color;
  final String label;

  const _Legend({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(label, style: context.texts.labelSmall),
      ],
    );
  }
}
