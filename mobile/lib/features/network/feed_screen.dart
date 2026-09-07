import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/common.dart';
import '../notifications/notification_providers.dart';

/// What the people you follow have been doing.
class FeedScreen extends ConsumerWidget {
  const FeedScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(feedProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Feed')),
      body: async.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(16),
          child: ListSkeleton(),
        ),
        error: (e, _) => ErrorState(
          error: e,
          onRetry: () => ref.invalidate(feedProvider),
        ),
        data: (items) {
          if (items.isEmpty) {
            return EmptyState(
              icon: Icons.dynamic_feed_outlined,
              title: 'Your feed is quiet',
              message: 'Follow players, teams and organizers to see what they '
                  'are up to.',
              actionLabel: 'Find people',
              onAction: () => context.push(Routes.network),
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(feedProvider),
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              itemCount: items.length,
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (context, i) {
                final a = items[i];
                return CnCard(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  onTap: a.link.isEmpty
                      ? null
                      : () => openServerLink(context, a.link),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      CnAvatar(name: a.actorName, size: 36),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            RichText(
                              text: TextSpan(
                                style: context.texts.bodySmall,
                                children: [
                                  TextSpan(
                                    text: a.actorName,
                                    style: const TextStyle(
                                        fontWeight: FontWeight.w700),
                                  ),
                                  TextSpan(text: ' ${a.text}'),
                                ],
                              ),
                            ),
                            const SizedBox(height: 4),
                            Row(
                              children: [
                                Icon(
                                  switch (a.kind) {
                                    'match' => Icons.sports_cricket,
                                    'tournament' => Icons.emoji_events_outlined,
                                    _ => Icons.groups_outlined,
                                  },
                                  size: 12,
                                  color: context.cric.faint,
                                ),
                                const SizedBox(width: 5),
                                Text(
                                  Fmt.timeAgo(a.when),
                                  style: context.texts.labelSmall
                                      ?.copyWith(color: context.cric.faint),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }

}
