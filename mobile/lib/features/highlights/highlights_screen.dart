import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/match.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';

final allHighlightsProvider =
    FutureProvider.autoDispose<List<MatchHighlightGroup>>(
  (ref) => ref.watch(apiProvider).allHighlights(),
);

/// Every clip anyone has attached to a match.
class HighlightsScreen extends ConsumerWidget {
  const HighlightsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(allHighlightsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Highlights')),
      body: async.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(16),
          child: ListSkeleton(),
        ),
        error: (e, _) => ErrorState(
          error: e,
          onRetry: () => ref.invalidate(allHighlightsProvider),
        ),
        data: (groups) {
          if (groups.isEmpty) {
            return const EmptyState(
              icon: Icons.play_circle_outline,
              title: 'No highlights yet',
              message:
                  'Clips added to any match show up here for everyone to watch.',
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(allHighlightsProvider),
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              itemCount: groups.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (context, i) => _GroupCard(group: groups[i]),
            ),
          );
        },
      ),
    );
  }
}

class _GroupCard extends StatelessWidget {
  final MatchHighlightGroup group;

  const _GroupCard({required this.group});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          InkWell(
            onTap: () => context.push(Routes.match(group.matchId)),
            child: Row(
              children: [
                if (group.live) ...[
                  const LiveDot(size: 7),
                  const SizedBox(width: 6),
                ],
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        group.title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: context.texts.bodyMedium
                            ?.copyWith(fontWeight: FontWeight.w700),
                      ),
                      Text(
                        '${group.statusLabel} · ${group.fmt} · '
                        '${group.clips.length} clip'
                        '${group.clips.length == 1 ? '' : 's'}',
                        style: context.texts.labelSmall,
                      ),
                    ],
                  ),
                ),
                Icon(Icons.chevron_right, size: 19, color: context.cric.faint),
              ],
            ),
          ),
          const SizedBox(height: 12),
          for (final clip in group.clips)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: InkWell(
                onTap: () async {
                  final uri = Uri.parse(clip.url);
                  if (!await launchUrl(uri,
                      mode: LaunchMode.externalApplication)) {
                    if (context.mounted) context.copyToClipboard(clip.url);
                  }
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: context.cric.surfaceVariant,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: context.cric.line),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.play_circle_fill,
                          size: 22, color: context.scheme.primary),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          clip.label ?? 'Watch clip',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: context.texts.bodySmall,
                        ),
                      ),
                      Icon(Icons.open_in_new,
                          size: 15, color: context.cric.faint),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
