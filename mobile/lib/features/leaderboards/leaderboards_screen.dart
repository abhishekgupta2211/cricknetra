import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/models/social.dart';
import '../../core/router/app_router.dart';
import '../../core/widgets/common.dart';
import '../home/home_screen.dart';
import 'leaderboard_providers.dart';

/// All twelve boards, filterable by time window and location.
class LeaderboardsScreen extends ConsumerWidget {
  const LeaderboardsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final query = ref.watch(leaderboardQueryProvider);
    final async = ref.watch(leaderboardsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Leaderboards'),
        actions: [
          IconButton(
            tooltip: 'Compare',
            icon: const Icon(Icons.compare_arrows, size: 22),
            onPressed: () => context.push(Routes.compare),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
            child: Column(
              children: [
                CnSegmented<String>(
                  selected: query.window,
                  onChanged: (v) => ref
                      .read(leaderboardQueryProvider.notifier)
                      .state = LeaderboardQuery(
                    window: v,
                    location: query.location,
                  ),
                  options: [
                    for (final e in Leaderboards.windows.entries)
                      (value: e.key, label: e.value),
                  ],
                ),
                if ((async.valueOrNull?.locations ?? const []).isNotEmpty) ...[
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String?>(
                    initialValue: query.location,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Location',
                      isDense: true,
                    ),
                    items: [
                      const DropdownMenuItem<String?>(
                        value: null,
                        child: Text('All locations'),
                      ),
                      for (final l in async.valueOrNull!.locations)
                        DropdownMenuItem<String?>(value: l, child: Text(l)),
                    ],
                    onChanged: (v) => ref
                        .read(leaderboardQueryProvider.notifier)
                        .state = LeaderboardQuery(
                      window: query.window,
                      location: v,
                    ),
                  ),
                ],
              ],
            ),
          ),
          Expanded(
            child: async.when(
              loading: () => const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16),
                child: ListSkeleton(rows: 4),
              ),
              error: (e, _) => ErrorState(
                error: e,
                onRetry: () => ref.invalidate(leaderboardsProvider),
              ),
              data: (boards) {
                if (boards.isEmpty) {
                  return EmptyState(
                    icon: Icons.leaderboard_outlined,
                    title: 'No stats for this period',
                    message: query.window == 'all' && query.location == null
                        ? 'Score a match and the boards fill in.'
                        : 'Try All time, or clear the location filter.',
                  );
                }
                final list = boards.nonEmptyBoards;
                return RefreshIndicator(
                  onRefresh: () async => ref.invalidate(leaderboardsProvider),
                  child: ListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
                    itemCount: list.length,
                    itemBuilder: (context, i) => _Board(board: list[i]),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _Board extends StatelessWidget {
  final LeaderboardBoard board;

  const _Board({required this.board});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionHeader(title: board.title),
        CnCard(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
          child: Column(
            children: [
              for (var i = 0; i < board.entries.length; i++)
                LeaderboardRow(rank: i + 1, entry: board.entries[i]),
            ],
          ),
        ),
      ],
    );
  }
}
