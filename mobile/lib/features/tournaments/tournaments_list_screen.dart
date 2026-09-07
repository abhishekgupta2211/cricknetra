import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/tournament.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'create_tournament_sheet.dart';
import 'tournament_providers.dart';

class TournamentsListScreen extends ConsumerStatefulWidget {
  const TournamentsListScreen({super.key});

  @override
  ConsumerState<TournamentsListScreen> createState() =>
      _TournamentsListScreenState();
}

class _TournamentsListScreenState
    extends ConsumerState<TournamentsListScreen> {
  final _search = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final created = await showModalBottomSheet<Tournament>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const CreateTournamentSheet(),
    );
    if (created == null || !mounted) return;
    ref.invalidate(tournamentsProvider);
    context.push(Routes.tournament(created.id));
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(tournamentsProvider);
    final canCreate =
        ref.watch(authControllerProvider).can(Caps.createTournament);

    return Scaffold(
      appBar: AppBar(title: const Text('Tournaments')),
      floatingActionButton: canCreate
          ? FloatingActionButton.extended(
              onPressed: _create,
              icon: const Icon(Icons.add),
              label: const Text('New tournament'),
            )
          : null,
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
            child: SearchField(
              controller: _search,
              hint: 'Search tournaments',
              onChanged: (v) => setState(() => _query = v),
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
                onRetry: () => ref.invalidate(tournamentsProvider),
              ),
              data: (all) {
                final q = _query.trim().toLowerCase();
                final list = all.where((t) {
                  if (q.isEmpty) return true;
                  return t.name.toLowerCase().contains(q) ||
                      TournamentFormats.label(t.format)
                          .toLowerCase()
                          .contains(q);
                }).toList();

                if (list.isEmpty) {
                  return EmptyState(
                    icon: Icons.emoji_events_outlined,
                    title: all.isEmpty
                        ? 'No tournaments yet'
                        : 'No tournaments found',
                    message: all.isEmpty
                        ? 'Run a league with a points table, or a straight knockout.'
                        : null,
                    actionLabel:
                        all.isEmpty && canCreate ? 'New tournament' : null,
                    onAction: all.isEmpty && canCreate ? _create : null,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async => ref.invalidate(tournamentsProvider),
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
                    itemCount: list.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, i) {
                      final t = list[i];
                      return CnCard(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 12),
                        onTap: () => context.push(Routes.tournament(t.id)),
                        child: Row(
                          children: [
                            Container(
                              width: 42,
                              height: 42,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                color: context.cric.amberSoft,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Icon(Icons.emoji_events,
                                  size: 20, color: context.cric.amber),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    t.name,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: context.texts.bodyMedium?.copyWith(
                                        fontWeight: FontWeight.w600),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(t.subtitle,
                                      style: context.texts.bodySmall),
                                ],
                              ),
                            ),
                            Icon(Icons.chevron_right,
                                size: 19, color: context.cric.faint),
                          ],
                        ),
                      );
                    },
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
