import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_config.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/roster.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'team_providers.dart';

class TeamsListScreen extends ConsumerStatefulWidget {
  const TeamsListScreen({super.key});

  @override
  ConsumerState<TeamsListScreen> createState() => _TeamsListScreenState();
}

class _TeamsListScreenState extends ConsumerState<TeamsListScreen> {
  final _search = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _createTeam() async {
    final name = await promptDialog(
      context,
      title: 'New team',
      hint: 'Team name',
      confirmLabel: 'Create',
    );
    if (name == null || !mounted) return;
    try {
      final team = await ref.read(apiProvider).createTeam(name: name);
      ref.invalidate(teamsProvider);
      if (!mounted) return;
      context.push(Routes.team(team.id));
    } catch (e) {
      if (mounted) context.toastError(e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(teamsProvider);
    final canCreate = ref.watch(authControllerProvider).can(Caps.createTeam);

    return Scaffold(
      appBar: AppBar(title: const Text('Teams')),
      floatingActionButton: canCreate
          ? FloatingActionButton.extended(
              onPressed: _createTeam,
              icon: const Icon(Icons.add),
              label: const Text('New team'),
            )
          : null,
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
            child: SearchField(
              controller: _search,
              hint: 'Search teams',
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
                onRetry: () => ref.invalidate(teamsProvider),
              ),
              data: (all) {
                final q = _query.trim().toLowerCase();
                final list = all.where((t) {
                  if (q.isEmpty) return true;
                  return t.name.toLowerCase().contains(q) ||
                      (t.location ?? '').toLowerCase().contains(q);
                }).toList();

                if (list.isEmpty) {
                  return EmptyState(
                    icon: Icons.groups_outlined,
                    title: all.isEmpty ? 'No teams yet' : 'No teams found',
                    message: all.isEmpty
                        ? 'Create a team, add players, then pick an XI at match time.'
                        : null,
                    actionLabel: all.isEmpty && canCreate ? 'New team' : null,
                    onAction: all.isEmpty && canCreate ? _createTeam : null,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async => ref.invalidate(teamsProvider),
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
                    itemCount: list.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, i) => TeamRow(team: list[i]),
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

class TeamRow extends StatelessWidget {
  final Team team;

  const TeamRow({super.key, required this.team});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      onTap: () => context.push(Routes.team(team.id)),
      child: Row(
        children: [
          CnAvatar(
            name: team.name,
            size: 42,
            imageUrl: team.hasPhoto ? ApiConfig.teamPhoto(team.id) : null,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  team.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 2),
                Text(team.subtitle, style: context.texts.bodySmall),
              ],
            ),
          ),
          Icon(Icons.chevron_right, size: 19, color: context.cric.faint),
        ],
      ),
    );
  }
}
