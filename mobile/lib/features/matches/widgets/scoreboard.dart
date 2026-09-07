import 'package:flutter/material.dart';

import '../../../core/models/match.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/utils/formatters.dart';
import '../../../core/widgets/common.dart';

/// The big score, the rate line and the current over — the panel a scorer
/// glances at between deliveries.
class Scoreboard extends StatelessWidget {
  final MatchState match;
  final Innings innings;

  const Scoreboard({super.key, required this.match, required this.innings});

  @override
  Widget build(BuildContext context) {
    final chasing = innings.isChase && !innings.isComplete;

    return CnCard(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '${innings.battingTeam} v ${innings.bowlingTeam}',
                  style: context.texts.titleSmall,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (match.isLive)
                Row(
                  children: [
                    const LiveDot(),
                    const SizedBox(width: 5),
                    Text(
                      'LIVE',
                      style: context.texts.labelSmall?.copyWith(
                        color: context.cric.wicket,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.6,
                      ),
                    ),
                  ],
                ),
            ],
          ),
          const SizedBox(height: 8),
          _BadgeRow(match: match, innings: innings),
          const SizedBox(height: 10),

          // The score itself.
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                innings.scoreLine,
                style: context.texts.displaySmall?.copyWith(
                  fontSize: 42,
                  height: 1,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
              const SizedBox(width: 12),
              Text(
                '${innings.oversStr} / ${innings.maxOvers} ov',
                style: context.texts.bodyMedium?.copyWith(
                  color: context.cric.muted,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Three numbers: always the run rate, then either the chase or the
          // first-innings projection.
          Row(
            children: [
              Expanded(
                child: StatTile(
                  label: 'CRR',
                  value: innings.runRate.toStringAsFixed(2),
                ),
              ),
              if (chasing) ...[
                Expanded(
                  child: StatTile(
                    label: 'REQ',
                    value: Fmt.rate(innings.requiredRunRate),
                    valueColor: context.cric.amber,
                  ),
                ),
                Expanded(
                  child: StatTile(
                    label: 'Target',
                    value: '${innings.target ?? 0}',
                  ),
                ),
              ] else ...[
                Expanded(
                  child: StatTile(
                    label: 'Extras',
                    value: '${innings.extras.total}',
                  ),
                ),
                Expanded(
                  child: StatTile(
                    label: 'Proj',
                    value: '${innings.projected}',
                  ),
                ),
              ],
            ],
          ),

          if (chasing && innings.requiredRuns != null) ...[
            const SizedBox(height: 10),
            Text(
              'Need ${innings.requiredRuns} off ${innings.ballsRemaining} '
              '${innings.ballsRemaining == 1 ? 'ball' : 'balls'}',
              style: context.texts.bodyMedium?.copyWith(
                color: context.scheme.primary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],

          const SizedBox(height: 14),
          ThisOverStrip(balls: innings.thisOver),

          if (match.result != null) ...[
            const SizedBox(height: 14),
            _Banner(
              text: match.result!,
              color: context.scheme.primary,
              icon: Icons.emoji_events_outlined,
            ),
          ] else if (innings.resultNote != null) ...[
            const SizedBox(height: 14),
            _Banner(
              text: innings.resultNote!,
              color: context.cric.muted,
              icon: Icons.info_outline,
            ),
          ],
        ],
      ),
    );
  }
}

class _BadgeRow extends StatelessWidget {
  final MatchState match;
  final Innings innings;

  const _BadgeRow({required this.match, required this.innings});

  @override
  Widget build(BuildContext context) {
    final badges = <Widget>[
      if (innings.isSuperOver)
        CnBadge(
          text: 'SUPER OVER',
          color: context.cric.six,
          icon: Icons.bolt,
        ),
      if (innings.freeHit)
        CnBadge(
          text: 'FREE HIT',
          color: context.cric.amber,
          filled: true,
        ),
      if (innings.inPowerplay)
        CnBadge(
          text: '${innings.powerplayLabel ?? 'Powerplay'}'
              '${innings.fieldersOutsideLimit == null ? '' : ' · ${innings.fieldersOutsideLimit} out'}',
          color: context.cric.four,
        ),
      CnBadge(text: match.rulesName, color: context.cric.muted),
      if (match.rules.superOverOnTie && !innings.isSuperOver)
        CnBadge(text: 'Super over', color: context.cric.muted),
      if (match.rules.dlsEnabled)
        CnBadge(text: 'DLS', color: context.cric.muted),
      if (match.rules.overBoundaryOut)
        CnBadge(text: 'Rule-out', color: context.cric.muted),
    ];

    if (badges.isEmpty) return const SizedBox.shrink();
    return Wrap(spacing: 6, runSpacing: 6, children: badges);
  }
}

/// The deliveries bowled in the over so far.
class ThisOverStrip extends StatelessWidget {
  final List<String> balls;

  const ThisOverStrip({super.key, required this.balls});

  @override
  Widget build(BuildContext context) {
    if (balls.isEmpty) {
      return Row(
        children: [
          Text('This over', style: context.texts.labelSmall),
          const SizedBox(width: 10),
          Text('—', style: context.texts.bodySmall),
        ],
      );
    }
    return SizedBox(
      height: 34,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: balls.length,
        separatorBuilder: (_, _) => const SizedBox(width: 6),
        itemBuilder: (context, i) => BallChip(token: balls[i]),
      ),
    );
  }
}

/// One delivery, coloured by what it was.
class BallChip extends StatelessWidget {
  final String token;

  const BallChip({super.key, required this.token});

  /// Tokens come from the server: "•", "1", "4", "6", "Wd", "n+Nb", "1L", "W".
  static ({Color fg, Color bg}) colorsFor(BuildContext context, String token) {
    final t = token.toUpperCase();
    if (t.contains('W') && !t.contains('WD')) {
      return (fg: context.cric.wicket, bg: context.cric.wicketSoft);
    }
    if (t.contains('WD') || t.contains('NB') || t.endsWith('B') ||
        t.endsWith('L')) {
      return (fg: context.cric.amber, bg: context.cric.amberSoft);
    }
    if (t == '6') return (fg: context.cric.six, bg: context.cric.sixSoft);
    if (t == '4') return (fg: context.cric.four, bg: context.cric.fourSoft);
    if (t == '•' || t == '0') {
      return (fg: context.cric.faint, bg: context.cric.surfaceVariant);
    }
    return (fg: context.scheme.onSurface, bg: context.cric.surfaceVariant);
  }

  @override
  Widget build(BuildContext context) {
    final c = colorsFor(context, token);
    return Container(
      constraints: const BoxConstraints(minWidth: 34),
      padding: const EdgeInsets.symmetric(horizontal: 8),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: c.bg,
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: c.fg.withValues(alpha: 0.3)),
      ),
      child: Text(
        token,
        style: context.texts.labelLarge?.copyWith(
          color: c.fg,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _Banner extends StatelessWidget {
  final String text;
  final Color color;
  final IconData icon;

  const _Banner({required this.text, required this.color, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Icon(icon, size: 17, color: color),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              text,
              style: context.texts.bodyMedium?.copyWith(
                color: color,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// The two batters at the crease and the bowler, above the pad.
class CreaseCard extends StatelessWidget {
  final Innings innings;

  const CreaseCard({super.key, required this.innings});

  @override
  Widget build(BuildContext context) {
    final striker = innings.strikerCard;
    final nonStriker = innings.nonStrikerCard;
    final bowler = innings.currentBowler;
    final stand = innings.currentPartnership;

    return CnCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Column(
        children: [
          if (striker != null)
            _BatterRow(card: striker, onStrike: true),
          if (nonStriker != null) ...[
            const SizedBox(height: 8),
            _BatterRow(card: nonStriker, onStrike: false),
          ],
          if (bowler != null) ...[
            Divider(height: 20, color: context.cric.line),
            Row(
              children: [
                Icon(Icons.sports_baseball_outlined,
                    size: 15, color: context.cric.faint),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    bowler.name,
                    style: context.texts.bodyMedium
                        ?.copyWith(fontWeight: FontWeight.w600),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Text(
                  '${bowler.wickets}/${bowler.runs} (${bowler.overs})',
                  style: context.texts.bodySmall?.copyWith(
                    fontFeatures: const [FontFeature.tabularFigures()],
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  'ec ${bowler.economy.toStringAsFixed(1)}',
                  style: context.texts.labelSmall
                      ?.copyWith(color: context.cric.faint),
                ),
              ],
            ),
          ],
          if (stand != null) ...[
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Partnership ${stand.runs} (${stand.balls})',
                style: context.texts.labelSmall
                    ?.copyWith(color: context.cric.faint),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _BatterRow extends StatelessWidget {
  final BatterCard card;
  final bool onStrike;

  const _BatterRow({required this.card, required this.onStrike});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 16,
          child: onStrike
              ? Icon(Icons.sports_cricket,
                  size: 14, color: context.scheme.primary)
              : null,
        ),
        Expanded(
          child: Text(
            card.name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: context.texts.bodyMedium?.copyWith(
              fontWeight: onStrike ? FontWeight.w700 : FontWeight.w500,
              color: onStrike ? context.scheme.primary : null,
            ),
          ),
        ),
        Text(
          card.figure,
          style: context.texts.bodyMedium?.copyWith(
            fontWeight: FontWeight.w700,
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
        const SizedBox(width: 10),
        SizedBox(
          width: 52,
          child: Text(
            'sr ${card.strikeRate.toStringAsFixed(0)}',
            textAlign: TextAlign.right,
            style: context.texts.labelSmall?.copyWith(color: context.cric.faint),
          ),
        ),
      ],
    );
  }
}
