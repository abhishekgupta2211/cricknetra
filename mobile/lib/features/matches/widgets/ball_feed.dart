import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/auth/auth_provider.dart';
import '../../../core/models/match.dart';
import '../../../core/models/rules.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/utils/formatters.dart';
import '../../../core/widgets/common.dart';
import '../match_providers.dart';
import 'capture_dialogs.dart';

/// Ball-by-ball commentary plus the scorer's manual notes.
///
/// A scorer can correct or remove any delivery in the live innings; the server
/// replays the log, so the scorecard recomputes rather than being patched.
class CommentaryTab extends ConsumerWidget {
  final String matchId;
  final bool canScore;
  final bool canCommentate;
  final Future<void> Function() onEdited;

  const CommentaryTab({
    super.key,
    required this.matchId,
    required this.canScore,
    required this.canCommentate,
    required this.onEdited,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feed = ref.watch(ballFeedProvider(matchId));

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(ballFeedProvider(matchId));
        ref.invalidate(commentaryProvider(matchId));
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          _CommentaryNotes(matchId: matchId, canPost: canCommentate),
          const SizedBox(height: 16),
          Text('Ball by ball', style: context.texts.titleSmall),
          const SizedBox(height: 10),
          feed.when(
            loading: () => const ListSkeleton(rows: 4),
            error: (e, _) => ErrorState(
              error: e,
              onRetry: () => ref.invalidate(ballFeedProvider(matchId)),
            ),
            data: (items) {
              if (items.isEmpty) {
                return const EmptyState(
                  icon: Icons.timeline_outlined,
                  title: 'No deliveries yet',
                  message: 'Every ball appears here as it is scored.',
                );
              }
              return _FeedList(
                items: items,
                matchId: matchId,
                canScore: canScore,
                onEdited: onEdited,
              );
            },
          ),
        ],
      ),
    );
  }
}

class _FeedList extends ConsumerWidget {
  final List<BallFeedItem> items;
  final String matchId;
  final bool canScore;
  final Future<void> Function() onEdited;

  const _FeedList({
    required this.items,
    required this.matchId,
    required this.canScore,
    required this.onEdited,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Newest over first, and newest ball first inside each over — the way a
    // live feed reads.
    final groups = <String, List<BallFeedItem>>{};
    for (final b in items) {
      groups.putIfAbsent('${b.innings}|${b.overNumber}', () => []).add(b);
    }
    final keys = groups.keys.toList().reversed.toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final key in keys) ...[
          Padding(
            padding: const EdgeInsets.fromLTRB(2, 12, 2, 6),
            child: Text(
              '${key.split('|').first} · Over ${int.parse(key.split('|').last) + 1}',
              style: context.texts.labelSmall?.copyWith(
                color: context.cric.faint,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.4,
              ),
            ),
          ),
          CnCard(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: Column(
              children: [
                for (final b in groups[key]!.reversed)
                  _BallRow(
                    ball: b,
                    matchId: matchId,
                    canScore: canScore,
                    onEdited: onEdited,
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _BallRow extends ConsumerWidget {
  final BallFeedItem ball;
  final String matchId;
  final bool canScore;
  final Future<void> Function() onEdited;

  const _BallRow({
    required this.ball,
    required this.matchId,
    required this.canScore,
    required this.onEdited,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final editable = canScore && ball.editable;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 34,
            child: Text(
              ball.overBall,
              style: context.texts.labelSmall?.copyWith(
                color: context.cric.faint,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ),
          const SizedBox(width: 6),
          BallChipSmall(kind: ball.kind, label: ball.badge),
          const SizedBox(width: 10),
          Expanded(
            child: Text(ball.text, style: context.texts.bodySmall),
          ),
          if (editable)
            SizedBox(
              width: 30,
              child: PopupMenuButton<String>(
                padding: EdgeInsets.zero,
                iconSize: 17,
                icon: Icon(Icons.more_vert, color: context.cric.faint),
                onSelected: (v) => _onAction(context, ref, v),
                itemBuilder: (context) => const [
                  PopupMenuItem(value: 'edit', child: Text('Correct this ball')),
                  PopupMenuItem(value: 'delete', child: Text('Remove this ball')),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _onAction(
      BuildContext context, WidgetRef ref, String action) async {
    final api = ref.read(apiProvider);
    final session = ref.read(matchControllerProvider(matchId)).valueOrNull;
    if (session == null) return;

    if (action == 'delete') {
      final ok = await confirmDialog(
        context,
        title: 'Remove this delivery?',
        message: 'The scorecard recomputes from the remaining balls.',
        confirmLabel: 'Remove',
      );
      if (!ok) return;
      try {
        await api.deleteBall(matchId, ball.idx);
        ref.invalidate(ballFeedProvider(matchId));
        await onEdited();
        if (context.mounted) context.toast('Delivery removed');
      } catch (e) {
        if (context.mounted) context.toastError(e);
      }
      return;
    }

    final innings = session.state.current;
    if (innings == null) return;
    final replacement = await showEditBallSheet(
      context,
      rules: session.state.rules,
      innings: innings,
      fielders: fieldingSideNames(session.state),
      wasFreeHit: ball.freeHit,
    );
    if (replacement == null || !context.mounted) return;
    try {
      await api.editBall(matchId, ball.idx, replacement);
      ref.invalidate(ballFeedProvider(matchId));
      await onEdited();
      if (context.mounted) context.toast('Delivery corrected');
    } catch (e) {
      if (context.mounted) context.toastError(e);
    }
  }
}

/// Pick the correct outcome for a delivery already in the log.
Future<BallRequest?> showEditBallSheet(
  BuildContext context, {
  required MatchRules rules,
  required Innings innings,
  required List<String> fielders,

  /// Whether the delivery being corrected was itself a free hit. `innings`
  /// carries the state for the NEXT ball, which is a different question.
  required bool wasFreeHit,
}) {
  return showModalBottomSheet<BallRequest>(
    context: context,
    isScrollControlled: true,
    builder: (sheetContext) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Correct this delivery',
                style: sheetContext.texts.titleMedium),
            const SizedBox(height: 4),
            Text(
              'Pick what actually happened. The scorecard recomputes.',
              style: sheetContext.texts.bodySmall,
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                for (final n in [0, 1, 2, 3, 4])
                  _EditChoice(
                    label: '$n',
                    onTap: () => Navigator.pop(
                      sheetContext,
                      BallRequest(action: BallRequest.actionRuns, value: n),
                    ),
                  ),
                // Mirror the pad: a rule-out format turns a six into a
                // dismissal, except on a free hit where it cannot apply.
                if (rules.overBoundaryOut && !wasFreeHit)
                  _EditChoice(
                    label: '6=OUT',
                    onTap: () => Navigator.pop(
                      sheetContext,
                      const BallRequest(
                        action: BallRequest.actionWicket,
                        dismissal: Dismissals.boundaryOut,
                      ),
                    ),
                  )
                else
                  _EditChoice(
                    label: '6',
                    onTap: () => Navigator.pop(
                      sheetContext,
                      const BallRequest(
                          action: BallRequest.actionRuns, value: 6),
                    ),
                  ),
                if (rules.wide.enabled)
                  _EditChoice(
                    label: 'Wd',
                    onTap: () => Navigator.pop(sheetContext,
                        const BallRequest(action: BallRequest.actionWide)),
                  ),
                if (rules.noBall.enabled)
                  _EditChoice(
                    label: 'Nb',
                    onTap: () => Navigator.pop(sheetContext,
                        const BallRequest(action: BallRequest.actionNoBall)),
                  ),
                if (rules.byesAllowed)
                  _EditChoice(
                    label: 'B',
                    onTap: () => Navigator.pop(
                      sheetContext,
                      const BallRequest(
                          action: BallRequest.actionBye, value: 1),
                    ),
                  ),
                if (rules.legByesAllowed)
                  _EditChoice(
                    label: 'Lb',
                    onTap: () => Navigator.pop(
                      sheetContext,
                      const BallRequest(
                          action: BallRequest.actionLegBye, value: 1),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 14),
            OutlinedButton(
              style: OutlinedButton.styleFrom(
                foregroundColor: sheetContext.cric.wicket,
              ),
              onPressed: () async {
                final choice = await showWicketDialog(
                  sheetContext,
                  rules: rules,
                  innings: innings,
                  fielders: fielders,
                  freeHit: wasFreeHit,
                );
                if (choice == null || !sheetContext.mounted) return;
                Navigator.pop(
                  sheetContext,
                  BallRequest(
                    action: BallRequest.actionWicket,
                    dismissal: choice.dismissal,
                    batterOut: choice.batterOut,
                    fielder: choice.fielder,
                    value: choice.runs,
                  ),
                );
              },
              child: const Text('It was a wicket'),
            ),
          ],
        ),
      ),
    ),
  );
}

class _EditChoice extends StatelessWidget {
  final String label;
  final VoidCallback onTap;

  const _EditChoice({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 64,
        height: 52,
        child: OutlinedButton(
          onPressed: onTap,
          child: Text(label, style: context.texts.titleMedium),
        ),
      );
}

/// A compact badge for the ball feed.
class BallChipSmall extends StatelessWidget {
  final String kind;
  final String label;

  const BallChipSmall({super.key, required this.kind, required this.label});

  @override
  Widget build(BuildContext context) {
    final color = switch (kind) {
      'wicket' => context.cric.wicket,
      'six' => context.cric.six,
      'four' => context.cric.four,
      'wide' || 'noball' || 'bye' || 'legbye' => context.cric.amber,
      'dot' => context.cric.faint,
      _ => context.scheme.onSurface,
    };
    return Container(
      width: 26,
      height: 22,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.13),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: context.texts.labelSmall
            ?.copyWith(color: color, fontWeight: FontWeight.w700, fontSize: 10),
      ),
    );
  }
}

/// Manual commentary notes, posted by anyone with the commentate capability.
class _CommentaryNotes extends ConsumerStatefulWidget {
  final String matchId;
  final bool canPost;

  const _CommentaryNotes({required this.matchId, required this.canPost});

  @override
  ConsumerState<_CommentaryNotes> createState() => _CommentaryNotesState();
}

class _CommentaryNotesState extends ConsumerState<_CommentaryNotes> {
  final _controller = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _post() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).postCommentary(widget.matchId, text);
      _controller.clear();
      ref.invalidate(commentaryProvider(widget.matchId));
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final notes = ref.watch(commentaryProvider(widget.matchId));

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(Icons.mic_none, size: 17, color: context.cric.muted),
              const SizedBox(width: 8),
              Text('Commentary', style: context.texts.titleSmall),
            ],
          ),
          if (widget.canPost) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    maxLength: 280,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _busy ? null : _post(),
                    decoration: const InputDecoration(
                      hintText: 'Add a note',
                      isDense: true,
                      counterText: '',
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                IconButton.filled(
                  onPressed: _busy ? null : _post,
                  icon: const Icon(Icons.send, size: 18),
                ),
              ],
            ),
          ],
          const SizedBox(height: 8),
          notes.when(
            loading: () => const SkeletonBox(height: 40),
            error: (_, _) => Text(
              'Could not load commentary.',
              style: context.texts.bodySmall,
            ),
            data: (list) {
              if (list.isEmpty) {
                return Text(
                  widget.canPost
                      ? 'No notes yet. Add the first one.'
                      : 'No commentary notes yet.',
                  style: context.texts.bodySmall,
                );
              }
              return Column(
                children: [
                  for (final n in list)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          CnAvatar(name: n.authorName, size: 26),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text(
                                      n.authorName,
                                      style: context.texts.labelLarge?.copyWith(
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Text(
                                      Fmt.timeAgo(n.when),
                                      style: context.texts.labelSmall
                                          ?.copyWith(color: context.cric.faint),
                                    ),
                                  ],
                                ),
                                Text(n.text, style: context.texts.bodySmall),
                              ],
                            ),
                          ),
                        ],
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
