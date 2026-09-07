import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/social.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/common.dart';
import 'notification_providers.dart';

/// Notifications, grouped by category. Opening the screen marks them read.
class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() =>
      _NotificationsScreenState();
}

class _NotificationsScreenState
    extends ConsumerState<NotificationsScreen> {
  String? _category;

  /// Ids removed locally, so a delete feels instant while the call runs.
  final _removed = <String>{};

  @override
  void initState() {
    super.initState();
    // Reading the list is what marks it read, so do it once on open.
    WidgetsBinding.instance.addPostFrameCallback((_) => _markRead());
  }

  Future<void> _markRead() async {
    try {
      await ref.read(apiProvider).markNotificationsRead();
      ref.invalidate(unreadNotificationsProvider);
    } catch (_) {
      // Not worth interrupting the user over.
    }
  }

  Future<void> _delete(AppNotification n) async {
    setState(() => _removed.add(n.id));
    try {
      await ref.read(apiProvider).deleteNotification(n.id);
    } catch (e) {
      if (!mounted) return;
      setState(() => _removed.remove(n.id));
      context.toastError(e);
    }
  }

  void _open(AppNotification n) {
    if (n.link.isEmpty) return;
    // Record the click for engagement stats, but do not block navigation.
    ref.read(apiProvider).markNotificationClicked(n.id).ignore();
    if (!openServerLink(context, n.link)) {
      context.toast('There is no screen for that yet.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(notificationsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          IconButton(
            tooltip: 'Notification settings',
            icon: const Icon(Icons.tune, size: 20),
            onPressed: () => context.push(Routes.settings),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: async.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(16),
          child: ListSkeleton(),
        ),
        error: (e, _) => ErrorState(
          error: e,
          onRetry: () => ref.invalidate(notificationsProvider),
        ),
        data: (all) {
          final live = all.where((n) => !_removed.contains(n.id)).toList();
          if (live.isEmpty) {
            return const EmptyState(
              icon: Icons.notifications_none,
              title: 'No notifications yet',
              message: 'Match updates and follows appear here.',
            );
          }

          // Only offer the categories actually present.
          final counts = <String, int>{};
          for (final n in live) {
            counts[n.effectiveCategory] =
                (counts[n.effectiveCategory] ?? 0) + 1;
          }
          final categories = NotificationCategories.order
              .where(counts.containsKey)
              .toList();

          final shown = _category == null
              ? live
              : live.where((n) => n.effectiveCategory == _category).toList();

          return Column(
            children: [
              if (categories.length > 1)
                Padding(
                  padding: const EdgeInsets.only(top: 8, bottom: 4),
                  child: ChipFilterBar<String?>(
                    selected: _category,
                    onChanged: (v) => setState(() => _category = v),
                    options: [
                      (value: null, label: 'All', count: live.length),
                      for (final c in categories)
                        (
                          value: c,
                          label: NotificationCategories.label(c),
                          count: counts[c],
                        ),
                    ],
                  ),
                ),
              Expanded(
                child: RefreshIndicator(
                  onRefresh: () async =>
                      ref.invalidate(notificationsProvider),
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 10, 16, 32),
                    itemCount: shown.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 8),
                    itemBuilder: (context, i) {
                      final n = shown[i];
                      return Dismissible(
                        key: ValueKey(n.id),
                        direction: DismissDirection.endToStart,
                        onDismissed: (_) => _delete(n),
                        background: Container(
                          alignment: Alignment.centerRight,
                          padding: const EdgeInsets.only(right: 20),
                          decoration: BoxDecoration(
                            color: context.cric.wicketSoft,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Icon(Icons.delete_outline,
                              color: context.cric.wicket),
                        ),
                        child: CnCard(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 12),
                          onTap: n.link.isEmpty ? null : () => _open(n),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                NotificationCategories.emoji(
                                    n.effectiveCategory),
                                style: const TextStyle(fontSize: 17),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.start,
                                  children: [
                                    if (n.title.isNotEmpty)
                                      Text(
                                        n.title,
                                        style: context.texts.bodyMedium
                                            ?.copyWith(
                                                fontWeight: FontWeight.w700),
                                      ),
                                    Text(n.text,
                                        style: context.texts.bodySmall),
                                    const SizedBox(height: 4),
                                    Text(
                                      Fmt.timeAgo(n.when),
                                      style: context.texts.labelSmall
                                          ?.copyWith(
                                              color: context.cric.faint),
                                    ),
                                  ],
                                ),
                              ),
                              if (n.count > 1) ...[
                                const SizedBox(width: 8),
                                CnBadge(text: 'x${n.count}'),
                              ],
                              if (!n.isRead) ...[
                                const SizedBox(width: 8),
                                Container(
                                  width: 7,
                                  height: 7,
                                  margin: const EdgeInsets.only(top: 6),
                                  decoration: BoxDecoration(
                                    color: context.scheme.primary,
                                    shape: BoxShape.circle,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
