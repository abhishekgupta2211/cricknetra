import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/models/match.dart';
import '../../../core/router/app_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/utils/formatters.dart';
import '../../../core/widgets/common.dart';

/// The full innings card: batters, bowlers, extras, fall of wickets and
/// partnerships — everything a printed scorecard carries.
class InningsScorecard extends StatelessWidget {
  final Innings innings;

  const InningsScorecard({super.key, required this.innings});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        CnCard(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      '${innings.battingTeam} batting',
                      style: context.texts.titleSmall,
                    ),
                  ),
                  Text(
                    '${innings.scoreLine} (${innings.oversStr})',
                    style: context.texts.titleSmall?.copyWith(
                      color: context.scheme.primary,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              const _BattingHeader(),
              const SizedBox(height: 4),
              if (innings.whoBatted.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  child: Text('Yet to bat', style: context.texts.bodySmall),
                )
              else
                for (final b in innings.whoBatted) _BatterRow(batter: b),
              Divider(height: 18, color: context.cric.line),
              Row(
                children: [
                  Expanded(
                    child: Text('Extras', style: context.texts.bodyMedium),
                  ),
                  Text(
                    innings.extras.breakdown,
                    style: context.texts.bodySmall,
                  ),
                  const SizedBox(width: 12),
                  Text(
                    '${innings.extras.total}',
                    style: context.texts.bodyMedium
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                ],
              ),
              const SizedBox(height: 10),
            ],
          ),
        ),
        const SizedBox(height: 12),
        CnCard(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('${innings.bowlingTeam} bowling',
                  style: context.texts.titleSmall),
              const SizedBox(height: 10),
              const _BowlingHeader(),
              const SizedBox(height: 4),
              if (innings.bowlers.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  child: Text('No overs bowled yet',
                      style: context.texts.bodySmall),
                )
              else
                for (final b in innings.bowlers) _BowlerRow(bowler: b),
            ],
          ),
        ),
        if (innings.fallOfWickets.isNotEmpty) ...[
          const SizedBox(height: 12),
          CnCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Fall of wickets', style: context.texts.titleSmall),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final f in innings.fallOfWickets)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 9, vertical: 5),
                        decoration: BoxDecoration(
                          color: context.cric.surfaceVariant,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: context.cric.line),
                        ),
                        child: Text(
                          f.label,
                          style: context.texts.labelSmall,
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ],
        if (innings.partnerships.isNotEmpty) ...[
          const SizedBox(height: 12),
          _Partnerships(partnerships: innings.partnerships),
        ],
      ],
    );
  }
}

class _BattingHeader extends StatelessWidget {
  const _BattingHeader();

  @override
  Widget build(BuildContext context) {
    final style = context.texts.labelSmall?.copyWith(
      color: context.cric.faint,
      fontWeight: FontWeight.w700,
      letterSpacing: 0.4,
    );
    return Row(
      children: [
        Expanded(child: Text('BATTER', style: style)),
        SizedBox(width: 34, child: Text('R', textAlign: TextAlign.right, style: style)),
        SizedBox(width: 34, child: Text('B', textAlign: TextAlign.right, style: style)),
        SizedBox(width: 28, child: Text('4s', textAlign: TextAlign.right, style: style)),
        SizedBox(width: 28, child: Text('6s', textAlign: TextAlign.right, style: style)),
        SizedBox(width: 46, child: Text('SR', textAlign: TextAlign.right, style: style)),
      ],
    );
  }
}

class _BatterRow extends StatelessWidget {
  final BatterCard batter;

  const _BatterRow({required this.batter});

  @override
  Widget build(BuildContext context) {
    final nums = context.texts.bodySmall?.copyWith(
      fontFeatures: const [FontFeature.tabularFigures()],
    );

    return InkWell(
      onTap: batter.playerId == null
          ? null
          : () => context.push(Routes.player(batter.playerId!)),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      if (batter.onStrike)
                        Padding(
                          padding: const EdgeInsets.only(right: 4),
                          child: Icon(Icons.sports_cricket,
                              size: 12, color: context.scheme.primary),
                        ),
                      Flexible(
                        child: Text(
                          batter.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: context.texts.bodyMedium?.copyWith(
                            fontWeight: batter.onStrike
                                ? FontWeight.w700
                                : FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                  Text(
                    batter.statusText,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.texts.labelSmall?.copyWith(
                      color: batter.out
                          ? context.cric.faint
                          : context.scheme.primary,
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(
              width: 34,
              child: Text('${batter.runs}',
                  textAlign: TextAlign.right,
                  style: nums?.copyWith(fontWeight: FontWeight.w700)),
            ),
            SizedBox(
              width: 34,
              child: Text('${batter.balls}',
                  textAlign: TextAlign.right, style: nums),
            ),
            SizedBox(
              width: 28,
              child: Text('${batter.fours}',
                  textAlign: TextAlign.right, style: nums),
            ),
            SizedBox(
              width: 28,
              child: Text('${batter.sixes}',
                  textAlign: TextAlign.right, style: nums),
            ),
            SizedBox(
              width: 46,
              child: Text(batter.strikeRate.toStringAsFixed(1),
                  textAlign: TextAlign.right, style: nums),
            ),
          ],
        ),
      ),
    );
  }
}

class _BowlingHeader extends StatelessWidget {
  const _BowlingHeader();

  @override
  Widget build(BuildContext context) {
    final style = context.texts.labelSmall?.copyWith(
      color: context.cric.faint,
      fontWeight: FontWeight.w700,
      letterSpacing: 0.4,
    );
    return Row(
      children: [
        Expanded(child: Text('BOWLER', style: style)),
        SizedBox(width: 38, child: Text('O', textAlign: TextAlign.right, style: style)),
        SizedBox(width: 28, child: Text('M', textAlign: TextAlign.right, style: style)),
        SizedBox(width: 34, child: Text('R', textAlign: TextAlign.right, style: style)),
        SizedBox(width: 28, child: Text('W', textAlign: TextAlign.right, style: style)),
        SizedBox(width: 46, child: Text('ECON', textAlign: TextAlign.right, style: style)),
      ],
    );
  }
}

class _BowlerRow extends StatelessWidget {
  final BowlerCard bowler;

  const _BowlerRow({required this.bowler});

  @override
  Widget build(BuildContext context) {
    final nums = context.texts.bodySmall?.copyWith(
      fontFeatures: const [FontFeature.tabularFigures()],
    );

    return InkWell(
      onTap: bowler.playerId == null
          ? null
          : () => context.push(Routes.player(bowler.playerId!)),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(
          children: [
            Expanded(
              child: Text(
                bowler.name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: context.texts.bodyMedium,
              ),
            ),
            SizedBox(
              width: 38,
              child: Text(bowler.overs,
                  textAlign: TextAlign.right, style: nums),
            ),
            SizedBox(
              width: 28,
              child: Text('${bowler.maidens}',
                  textAlign: TextAlign.right, style: nums),
            ),
            SizedBox(
              width: 34,
              child: Text('${bowler.runs}',
                  textAlign: TextAlign.right, style: nums),
            ),
            SizedBox(
              width: 28,
              child: Text('${bowler.wickets}',
                  textAlign: TextAlign.right,
                  style: nums?.copyWith(fontWeight: FontWeight.w700)),
            ),
            SizedBox(
              width: 46,
              child: Text(bowler.economy.toStringAsFixed(1),
                  textAlign: TextAlign.right, style: nums),
            ),
          ],
        ),
      ),
    );
  }
}

class _Partnerships extends StatelessWidget {
  final List<Partnership> partnerships;

  const _Partnerships({required this.partnerships});

  @override
  Widget build(BuildContext context) {
    var best = 0;
    for (final p in partnerships) {
      if (p.runs > best) best = p.runs;
    }

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Partnerships', style: context.texts.titleSmall),
          const SizedBox(height: 10),
          for (final p in partnerships)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Row(
                children: [
                  SizedBox(
                    width: 34,
                    child: Text(
                      Fmt.ordinal(p.wicket),
                      style: context.texts.labelSmall
                          ?.copyWith(color: context.cric.faint),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      '${p.batterA} & ${p.batterB}'
                      '${p.unbroken ? ' (not out)' : ''}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.texts.bodySmall,
                    ),
                  ),
                  if (p.runs == best && best > 0) ...[
                    const CnBadge(text: 'Best'),
                    const SizedBox(width: 8),
                  ],
                  Text(
                    '${p.runs} (${p.balls})',
                    style: context.texts.bodySmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      fontFeatures: const [FontFeature.tabularFigures()],
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

/// Player of the match and the best performers, once the result is in.
class AwardsCard extends StatelessWidget {
  final MatchAwards awards;

  const AwardsCard({super.key, required this.awards});

  @override
  Widget build(BuildContext context) {
    if (awards.isEmpty) return const SizedBox.shrink();

    Widget row(String label, AwardEntry? entry, IconData icon) {
      if (entry == null) return const SizedBox.shrink();
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            Icon(icon, size: 17, color: context.cric.amber),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    entry.name,
                    style: context.texts.bodyMedium
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  Text(
                    '$label${entry.line.isEmpty ? '' : ' · ${entry.line}'}',
                    style: context.texts.labelSmall,
                  ),
                ],
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
          Text('Awards', style: context.texts.titleSmall),
          const SizedBox(height: 4),
          row('Player of the Match', awards.manOfTheMatch, Icons.star),
          row('Best batter', awards.bestBatter, Icons.sports_cricket),
          row('Best bowler', awards.bestBowler, Icons.sports_baseball),
        ],
      ),
    );
  }
}
