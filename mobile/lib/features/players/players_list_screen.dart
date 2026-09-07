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
import 'player_providers.dart';

class PlayersListScreen extends ConsumerStatefulWidget {
  const PlayersListScreen({super.key});

  @override
  ConsumerState<PlayersListScreen> createState() => _PlayersListScreenState();
}

class _PlayersListScreenState extends ConsumerState<PlayersListScreen> {
  final _search = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final result = await showModalBottomSheet<Player>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const PlayerFormSheet(),
    );
    if (result == null || !mounted) return;
    ref.invalidate(playersProvider);
    context.push(Routes.player(result.id));
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(playersProvider);
    final canCreate = ref.watch(authControllerProvider).can(Caps.createTeam);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Players'),
        actions: [
          IconButton(
            tooltip: 'Compare players',
            icon: const Icon(Icons.compare_arrows, size: 22),
            onPressed: () => context.push(Routes.compare),
          ),
          const SizedBox(width: 6),
        ],
      ),
      floatingActionButton: canCreate
          ? FloatingActionButton.extended(
              onPressed: _create,
              icon: const Icon(Icons.add),
              label: const Text('New player'),
            )
          : null,
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
            child: SearchField(
              controller: _search,
              hint: 'Search by name or code',
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
                onRetry: () => ref.invalidate(playersProvider),
              ),
              data: (all) {
                // The list endpoint takes no query parameter, so filtering
                // happens here on the full roster.
                final q = _query.trim().toLowerCase();
                final list = all.where((p) {
                  if (q.isEmpty) return true;
                  return p.name.toLowerCase().contains(q) ||
                      p.code.toLowerCase().contains(q);
                }).toList();

                if (list.isEmpty) {
                  return EmptyState(
                    icon: Icons.person_outline,
                    title: all.isEmpty ? 'No players yet' : 'No players found',
                    message: all.isEmpty
                        ? 'Add players so matches build their career records.'
                        : null,
                    actionLabel: all.isEmpty && canCreate ? 'New player' : null,
                    onAction: all.isEmpty && canCreate ? _create : null,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async => ref.invalidate(playersProvider),
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
                    itemCount: list.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, i) => PlayerRow(player: list[i]),
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

class PlayerRow extends StatelessWidget {
  final Player player;

  const PlayerRow({super.key, required this.player});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      onTap: () => context.push(Routes.player(player.id)),
      child: Row(
        children: [
          CnAvatar(
            name: player.name,
            size: 40,
            imageUrl:
                player.hasPhoto ? ApiConfig.playerPhoto(player.id) : null,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        player.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: context.texts.bodyMedium
                            ?.copyWith(fontWeight: FontWeight.w600),
                      ),
                    ),
                    if (player.isClaimed) ...[
                      const SizedBox(width: 6),
                      Icon(Icons.verified,
                          size: 14, color: context.scheme.primary),
                    ],
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  player.code.isEmpty
                      ? player.styleLine
                      : '${player.code} · ${player.styleLine}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.bodySmall,
                ),
              ],
            ),
          ),
          Icon(Icons.chevron_right, size: 19, color: context.cric.faint),
        ],
      ),
    );
  }
}

/// Create or edit a player.
class PlayerFormSheet extends ConsumerStatefulWidget {
  final Player? existing;

  const PlayerFormSheet({super.key, this.existing});

  @override
  ConsumerState<PlayerFormSheet> createState() => _PlayerFormSheetState();
}

class _PlayerFormSheetState extends ConsumerState<PlayerFormSheet> {
  late final _name = TextEditingController(text: widget.existing?.name ?? '');
  late final _phone = TextEditingController(text: widget.existing?.phone ?? '');
  late String? _batting = widget.existing?.battingStyle;
  late String? _bowling = widget.existing?.bowlingStyle;
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final name = _name.text.trim();
    if (name.isEmpty) {
      context.toast('Name the player');
      return;
    }
    setState(() => _busy = true);
    try {
      final api = ref.read(apiProvider);
      final saved = widget.existing == null
          ? await api.createPlayer(
              name: name,
              phone: _phone.text.trim(),
              battingStyle: _batting,
              bowlingStyle: _bowling,
            )
          : await api.updatePlayer(widget.existing!.id, {
              'name': name,
              'phone': _phone.text.trim(),
              // The server skips null on a partial update, so "—" has to be
              // sent as an empty string to actually clear the field.
              'batting_style': _batting ?? '',
              'bowling_style': _bowling ?? '',
            });
      if (!mounted) return;
      Navigator.pop(context, saved);
    } catch (e) {
      if (!mounted) return;
      context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 8,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              widget.existing == null ? 'New player' : 'Edit player',
              style: context.texts.titleMedium,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _name,
              textCapitalization: TextCapitalization.words,
              decoration:
                  const InputDecoration(labelText: 'Name', isDense: true),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _phone,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(
                labelText: 'Phone (optional)',
                helperText: 'Lets the player claim this profile later',
                isDense: true,
              ),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String?>(
              initialValue: _batting,
              isExpanded: true,
              decoration: const InputDecoration(
                  labelText: 'Batting style', isDense: true),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('—')),
                for (final s in Player.battingStyles)
                  DropdownMenuItem<String?>(value: s, child: Text(s)),
              ],
              onChanged: (v) => setState(() => _batting = v),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String?>(
              initialValue: _bowling,
              isExpanded: true,
              decoration: const InputDecoration(
                  labelText: 'Bowling style', isDense: true),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('—')),
                for (final s in Player.bowlingStyles)
                  DropdownMenuItem<String?>(value: s, child: Text(s)),
              ],
              onChanged: (v) => setState(() => _bowling = v),
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _busy ? null : _save,
              child: Text(widget.existing == null ? 'Add player' : 'Save'),
            ),
          ],
        ),
      ),
    );
  }
}
