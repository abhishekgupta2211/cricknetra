import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/match.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/widgets/common.dart';
import '../home/home_screen.dart';
import 'match_providers.dart';

/// Every match, filterable by state and searchable by team name.
class MatchesListScreen extends ConsumerStatefulWidget {
  const MatchesListScreen({super.key});

  @override
  ConsumerState<MatchesListScreen> createState() => _MatchesListScreenState();
}

enum _Filter { all, live, finished }

class _MatchesListScreenState extends ConsumerState<MatchesListScreen> {
  final _search = TextEditingController();
  _Filter _filter = _Filter.all;
  String _query = '';

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  List<MatchSummary> _apply(List<MatchSummary> all) {
    final q = _query.trim().toLowerCase();
    return all.reversed.where((m) {
      final matchesFilter = switch (_filter) {
        _Filter.all => true,
        _Filter.live => m.isLive,
        _Filter.finished => !m.isLive,
      };
      if (!matchesFilter) return false;
      if (q.isEmpty) return true;
      return m.teamA.toLowerCase().contains(q) ||
          m.teamB.toLowerCase().contains(q);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(matchesListProvider);
    final canScore = ref.watch(authControllerProvider).can(Caps.createMatch);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Matches'),
        actions: [
          if (canScore)
            IconButton(
              icon: const Icon(Icons.add, size: 22),
              tooltip: 'New match',
              onPressed: () => context.push(Routes.newMatch),
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
                SearchField(
                  controller: _search,
                  hint: 'Search by team',
                  onChanged: (v) => setState(() => _query = v),
                ),
                const SizedBox(height: 10),
                CnSegmented<_Filter>(
                  selected: _filter,
                  onChanged: (v) => setState(() => _filter = v),
                  options: const [
                    (value: _Filter.all, label: 'All'),
                    (value: _Filter.live, label: 'Live'),
                    (value: _Filter.finished, label: 'Finished'),
                  ],
                ),
              ],
            ),
          ),
          Expanded(
            child: async.when(
              loading: () => const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16),
                child: ListSkeleton(),
              ),
              error: (e, _) => ErrorState(
                error: e,
                onRetry: () => ref.invalidate(matchesListProvider),
              ),
              data: (all) {
                final list = _apply(all);
                if (list.isEmpty) {
                  return EmptyState(
                    icon: Icons.sports_cricket_outlined,
                    title: all.isEmpty
                        ? 'No matches yet'
                        : 'No matches match your filter',
                    message: all.isEmpty
                        ? 'Start scoring and it appears here.'
                        : null,
                    actionLabel: all.isEmpty && canScore ? 'New match' : null,
                    onAction: all.isEmpty && canScore
                        ? () => context.push(Routes.newMatch)
                        : null,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async => ref.invalidate(matchesListProvider),
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
                    itemCount: list.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, i) =>
                        MatchRowCard(match: list[i]),
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
