import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_config.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/match.dart';
import '../../core/models/user.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'match_providers.dart';
import 'widgets/ball_feed.dart';
import 'widgets/dls_panel.dart';
import 'widgets/match_charts.dart';
import 'widgets/match_extras.dart';
import 'widgets/scoreboard.dart';
import 'widgets/scorecard.dart';
import 'widgets/scoring_pad.dart';

/// The match console: score, pad, scorecard, ball feed, charts and the tools a
/// scorer needs during play.
class MatchScreen extends ConsumerStatefulWidget {
  final String matchId;

  const MatchScreen({super.key, required this.matchId});

  @override
  ConsumerState<MatchScreen> createState() => _MatchScreenState();
}

class _MatchScreenState extends ConsumerState<MatchScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 5, vsync: this);

  /// Which innings the scorecard and charts show; defaults to the live one.
  int? _viewInnings;

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(matchControllerProvider(widget.matchId));

    return Scaffold(
      appBar: AppBar(
        title: Text(async.valueOrNull?.state.title ?? 'Match'),
        actions: [
          IconButton(
            tooltip: 'Share scorecard',
            icon: const Icon(Icons.ios_share, size: 20),
            onPressed: () => context.copyToClipboard(
              ApiConfig.matchShareUrl(widget.matchId),
              message: 'Share link copied',
            ),
          ),
          if (async.valueOrNull != null)
            PopupMenuButton<String>(
              onSelected: (v) => _onMenu(v, async.valueOrNull!),
              itemBuilder: (context) => [
                const PopupMenuItem(
                  value: 'pdf',
                  child: ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(Icons.picture_as_pdf_outlined, size: 20),
                    title: Text('Printable scorecard'),
                  ),
                ),
                const PopupMenuItem(
                  value: 'public',
                  child: ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(Icons.public, size: 20),
                    title: Text('Open public page'),
                  ),
                ),
                if (ref.read(authControllerProvider).isAdmin)
                  const PopupMenuItem(
                    value: 'delete',
                    child: ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      leading: Icon(Icons.delete_outline, size: 20),
                      title: Text('Delete match'),
                    ),
                  ),
              ],
            ),
        ],
        bottom: TabBar(
          controller: _tabs,
          // Five short labels fit a phone if they share the width. Scrolling
          // them clipped the last tab to a bare "M" against the edge, which
          // reads as broken rather than as "there is more over here".
          isScrollable: false,
          labelPadding: const EdgeInsets.symmetric(horizontal: 4),
          tabs: const [
            Tab(text: 'Live'),
            Tab(text: 'Card'),
            Tab(text: 'Comms'),
            Tab(text: 'Charts'),
            Tab(text: 'More'),
          ],
        ),
      ),
      body: async.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(16),
          child: ListSkeleton(rows: 4),
        ),
        error: (e, _) => ErrorState(
          error: e,
          onRetry: () =>
              ref.read(matchControllerProvider(widget.matchId).notifier).load(),
        ),
        data: (session) => TabBarView(
          controller: _tabs,
          children: [
            _liveTab(session),
            _scorecardTab(session),
            _commentaryTab(session),
            _chartsTab(session),
            _moreTab(session),
          ],
        ),
      ),
    );
  }

  Future<void> _onMenu(String value, MatchSession session) async {
    switch (value) {
      case 'pdf':
        await _open(ApiConfig.scorecardPdfUrl(widget.matchId));
      case 'public':
        await _open(ApiConfig.matchShareUrl(widget.matchId));
      case 'delete':
        final ok = await confirmDialog(
          context,
          title: 'Delete match?',
          message:
              'The ball log and every stat derived from it go with it. This '
              'cannot be undone.',
        );
        if (!ok || !mounted) return;
        try {
          await ref.read(apiProvider).deleteMatch(widget.matchId);
          if (!mounted) return;
          context.toast('Match deleted');
          context.pop();
        } catch (e) {
          if (mounted) context.toastError(e);
        }
    }
  }

  Future<void> _open(String url) async {
    final uri = Uri.parse(url);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      if (mounted) context.copyToClipboard(url, message: 'Link copied');
    }
  }

  MatchController get _controller =>
      ref.read(matchControllerProvider(widget.matchId).notifier);

  // ------------------------------------------------------------- live tab

  Widget _liveTab(MatchSession session) {
    final match = session.state;
    final innings = match.current;
    if (innings == null) {
      return const EmptyState(
        icon: Icons.sports_cricket_outlined,
        title: 'This match has not started',
      );
    }

    return RefreshIndicator(
      onRefresh: _controller.refresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          if (!match.meta.isEmpty) ...[
            Text(
              match.meta.headline,
              style: context.texts.labelSmall?.copyWith(
                color: context.cric.faint,
                letterSpacing: 0.4,
              ),
            ),
            if (match.meta.tossText != null)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text(
                  match.meta.tossText!,
                  style: context.texts.labelSmall
                      ?.copyWith(color: context.cric.faint),
                ),
              ),
            const SizedBox(height: 12),
          ],
          Scoreboard(match: match, innings: innings),
          const SizedBox(height: 12),
          if (innings.striker != null) CreaseCard(innings: innings),

          if (session.canScore && !innings.isComplete) ...[
            const SizedBox(height: 12),
            ScoringPad(
              match: match,
              innings: innings,
              onBall: (ball) =>
                  _controller.act(() => ref.read(apiProvider).recordBall(
                        widget.matchId,
                        ball,
                      )),
              onSetBowler: (bowler) =>
                  _controller.act(() => ref.read(apiProvider).setBowler(
                        widget.matchId,
                        bowler,
                      )),
              onUndo: () => _controller
                  .act(() => ref.read(apiProvider).undo(widget.matchId)),
            ),
          ],

          if (session.canScore) ...[
            const SizedBox(height: 12),
            InningsActions(
              match: match,
              innings: innings,
              matchId: widget.matchId,
              controller: _controller,
            ),
          ],

          if (match.dls != null && session.canScore) ...[
            const SizedBox(height: 12),
            DlsPanel(
              matchId: widget.matchId,
              dls: match.dls!,
              innings: innings,
              controller: _controller,
            ),
          ] else if (match.dls != null && match.dls!.hasSummary) ...[
            const SizedBox(height: 12),
            DlsSummary(dls: match.dls!, innings: innings),
          ],

          if (match.awards != null && !match.awards!.isEmpty) ...[
            const SizedBox(height: 12),
            AwardsCard(awards: match.awards!),
          ],

          if (match.stream != null || session.canScore) ...[
            const SizedBox(height: 12),
            StreamPanel(
              matchId: widget.matchId,
              stream: match.stream,
              canManage: session.canScore,
              onChanged: _controller.refresh,
            ),
          ],

          const SizedBox(height: 12),
          KeyMomentsCard(matchId: widget.matchId),
        ],
      ),
    );
  }

  // -------------------------------------------------------- scorecard tab

  Widget _scorecardTab(MatchSession session) {
    final match = session.state;
    if (match.innings.isEmpty) {
      return const EmptyState(
        icon: Icons.table_chart_outlined,
        title: 'No innings yet',
      );
    }

    final index = (_viewInnings ?? match.currentInnings - 1)
        .clamp(0, match.innings.length - 1);

    return RefreshIndicator(
      onRefresh: _controller.refresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          if (match.innings.length > 1) ...[
            CnSegmented<int>(
              selected: index,
              onChanged: (v) => setState(() => _viewInnings = v),
              options: [
                for (var i = 0; i < match.innings.length; i++)
                  (
                    value: i,
                    label: match.innings[i].isSuperOver
                        ? 'Super ${match.innings[i].battingTeam}'
                        : match.innings[i].battingTeam,
                  ),
              ],
            ),
            const SizedBox(height: 14),
          ],
          InningsScorecard(innings: match.innings[index]),
          const SizedBox(height: 12),
          FieldingLog(
            matchId: widget.matchId,
            match: match,
            canScore: session.canScore,
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------- commentary tab

  Widget _commentaryTab(MatchSession session) {
    return CommentaryTab(
      matchId: widget.matchId,
      canScore: session.canScore,
      canCommentate: ref.watch(authControllerProvider).can(Caps.commentate),
      onEdited: _controller.refresh,
    );
  }

  // ----------------------------------------------------------- charts tab

  Widget _chartsTab(MatchSession session) {
    final match = session.state;
    final index = (_viewInnings ?? match.currentInnings - 1)
        .clamp(0, match.innings.isEmpty ? 0 : match.innings.length - 1);
    if (match.innings.isEmpty) {
      return const EmptyState(
        icon: Icons.insights_outlined,
        title: 'Charts appear once overs are bowled',
      );
    }
    final innings = match.innings[index];

    return DefaultTabController(
      length: 4,
      child: Column(
        children: [
          if (match.innings.length > 1)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
              child: CnSegmented<int>(
                selected: index,
                onChanged: (v) => setState(() => _viewInnings = v),
                options: [
                  for (var i = 0; i < match.innings.length; i++)
                    (value: i, label: match.innings[i].battingTeam),
                ],
              ),
            ),
          const TabBar(
            // Four charts share the width rather than scrolling, which was
            // clipping "Pitch map" on first render.
            isScrollable: false,
            labelPadding: EdgeInsets.symmetric(horizontal: 4),
            tabs: [
              Tab(text: 'Manhattan'),
              Tab(text: 'Worm'),
              Tab(text: 'Wagon'),
              Tab(text: 'Pitch'),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: [
                _chartPage(ManhattanChart(innings: innings)),
                _chartPage(WormChart(innings: match.mainInnings)),
                _chartPage(WagonWheel(shots: innings.wagon)),
                _chartPage(PitchMap(marks: innings.pitch)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _chartPage(Widget chart) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: CnCard(child: chart),
      );

  // ------------------------------------------------------------- more tab

  Widget _moreTab(MatchSession session) {
    final match = session.state;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: [
        MatchInfoCard(match: match),
        const SizedBox(height: 12),
        OfficialsPanel(
          matchId: widget.matchId,
          officials: session.officials,
          onChanged: _controller.refresh,
        ),
        const SizedBox(height: 12),
        ClipsPanel(
          matchId: widget.matchId,
          clips: match.clips,
          canManage: session.isManager,
          onChanged: _controller.refresh,
        ),
        if (session.canScore) ...[
          const SizedBox(height: 12),
          BroadcastPanel(matchId: widget.matchId),
        ],
      ],
    );
  }
}

/// Innings transitions the scorer drives: second innings, declaration, super
/// over. Each one is offered only when the server says it is available.
class InningsActions extends ConsumerStatefulWidget {
  final MatchState match;
  final Innings innings;
  final String matchId;
  final MatchController controller;

  const InningsActions({
    super.key,
    required this.match,
    required this.innings,
    required this.matchId,
    required this.controller,
  });

  @override
  ConsumerState<InningsActions> createState() => _InningsActionsState();
}

class _InningsActionsState extends ConsumerState<InningsActions> {
  bool _busy = false;

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

  @override
  Widget build(BuildContext context) {
    final api = ref.read(apiProvider);
    final m = widget.match;
    final actions = <Widget>[];

    if (m.showSecondInningsAction) {
      actions.add(
        ElevatedButton.icon(
          onPressed:
              _busy ? null : () => _run(() => api.startSecondInnings(m.id)),
          icon: const Icon(Icons.play_arrow, size: 18),
          label: const Text('Start 2nd innings'),
        ),
      );
    }

    if (m.needsSuperOver) {
      actions.add(
        Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Scores level — super over',
              style: context.texts.titleSmall,
            ),
            const SizedBox(height: 4),
            Text(
              'One over each, all out at two wickets. Who bats first?',
              style: context.texts.bodySmall,
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _busy
                        ? null
                        : () => _run(
                            () => api.startSuperOver(m.id, batFirst: 'a')),
                    child: Text(m.teamA, overflow: TextOverflow.ellipsis),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(
                    onPressed: _busy
                        ? null
                        : () => _run(
                            () => api.startSuperOver(m.id, batFirst: 'b')),
                    child: Text(m.teamB, overflow: TextOverflow.ellipsis),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
    }

    if (m.awaitingSuperSecond) {
      actions.add(
        ElevatedButton.icon(
          onPressed: _busy ? null : () => _run(() => api.startSuperOver(m.id)),
          icon: const Icon(Icons.play_arrow, size: 18),
          label: const Text('Start the super-over reply'),
        ),
      );
    }

    if (m.rules.allowDeclaration &&
        !widget.innings.isComplete &&
        !widget.innings.isSuperOver &&
        m.result == null) {
      actions.add(
        OutlinedButton.icon(
          onPressed: _busy
              ? null
              : () async {
                  final ok = await confirmDialog(
                    context,
                    title: 'Declare the innings?',
                    message: 'The innings closes here and cannot be reopened.',
                    confirmLabel: 'Declare',
                    destructive: false,
                  );
                  if (ok) await _run(() => api.declareInnings(m.id));
                },
          icon: const Icon(Icons.flag_outlined, size: 18),
          label: const Text('Declare innings'),
        ),
      );
    }

    if (actions.isEmpty) return const SizedBox.shrink();

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var i = 0; i < actions.length; i++) ...[
            if (i > 0) const SizedBox(height: 10),
            actions[i],
          ],
        ],
      ),
    );
  }
}

/// Venue, toss and rulebook, for the More tab.
class MatchInfoCard extends StatelessWidget {
  final MatchState match;

  const MatchInfoCard({super.key, required this.match});

  @override
  Widget build(BuildContext context) {
    final rules = match.rules;
    final rows = <({String label, String value})>[
      (label: 'Format', value: match.rulesName),
      (label: 'Overs', value: '${rules.oversPerInnings}'),
      (label: 'Squad', value: '${rules.playersPerSide}-a-side'),
      (label: 'Ball', value: BallTypeLabel.of(rules.ballType)),
      if (rules.maxOversPerBowler != null)
        (label: 'Max/bowler', value: '${rules.maxOversPerBowler}'),
      if (match.meta.venue != null)
        (label: 'Venue', value: match.meta.venue!),
      if (match.meta.tournament != null)
        (label: 'Tournament', value: match.meta.tournament!),
      if (match.meta.matchNo != null)
        (label: 'Match', value: match.meta.matchNo!),
      (label: 'Bats first', value: match.batFirst),
    ];

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Match details', style: context.texts.titleSmall),
          const SizedBox(height: 14),
          // Names, not numbers: two wider columns that wrap, so a ground
          // or a team is readable rather than ellipsised.
          StatGrid(stats: rows, columns: 2, valueMaxLines: 2),
          if (match.meta.tossText != null) ...[
            const SizedBox(height: 14),
            Text(match.meta.tossText!, style: context.texts.bodySmall),
          ],
          const SizedBox(height: 14),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              if (rules.overBoundaryOut)
                const CnBadge(text: 'Rule-out (six is out)'),
              if (rules.lastManStands) const CnBadge(text: 'Last man stands'),
              if (rules.superOverOnTie) const CnBadge(text: 'Super over'),
              if (rules.dlsEnabled) const CnBadge(text: 'DLS'),
              if (rules.allowDeclaration) const CnBadge(text: 'Declarations'),
              for (final pp in rules.powerplays)
                CnBadge(
                  text: '${pp.label} ${pp.startOver}-${pp.endOver}',
                ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Small helper so the info card need not import the rules model directly.
class BallTypeLabel {
  const BallTypeLabel._();
  static String of(String kind) => switch (kind) {
        'leather' => 'Leather',
        'tennis' => 'Tennis',
        _ => 'Other',
      };
}

/// Auto-generated key moments from the ball log.
class KeyMomentsCard extends ConsumerWidget {
  final String matchId;

  const KeyMomentsCard({super.key, required this.matchId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(matchHighlightsProvider(matchId));

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Key moments', style: context.texts.titleSmall),
          const SizedBox(height: 10),
          async.when(
            loading: () => const SkeletonBox(height: 50),
            error: (_, _) => Text(
              'Could not load key moments.',
              style: context.texts.bodySmall,
            ),
            data: (moments) {
              if (moments.isEmpty) {
                return Text(
                  'Wickets, boundaries and milestones appear here as the match '
                  'is scored.',
                  style: context.texts.bodySmall,
                );
              }
              final shown = moments.reversed.take(12).toList();
              return Column(
                children: [
                  for (final m in shown)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 5),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _MomentBadge(kind: m.kind),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  m.title,
                                  style: context.texts.labelLarge
                                      ?.copyWith(fontWeight: FontWeight.w700),
                                ),
                                Text(m.text, style: context.texts.bodySmall),
                              ],
                            ),
                          ),
                          if (m.overBall.isNotEmpty)
                            Text(
                              m.overBall,
                              style: context.texts.labelSmall
                                  ?.copyWith(color: context.cric.faint),
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

class _MomentBadge extends StatelessWidget {
  final String kind;

  const _MomentBadge({required this.kind});

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (kind) {
      'wicket' => ('W', context.cric.wicket),
      'six' => ('6', context.cric.six),
      'four' => ('4', context.cric.four),
      'fifty' => ('50', context.cric.amber),
      'hundred' => ('100', context.cric.amber),
      'bowling' => ('\u{1f3af}', context.cric.wicket),
      'result' => ('\u{1f3c6}', context.scheme.primary),
      _ => ('\u{2691}', context.cric.muted),
    };
    return Container(
      width: 30,
      height: 24,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(7),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: context.texts.labelSmall
            ?.copyWith(color: color, fontWeight: FontWeight.w800),
      ),
    );
  }
}
