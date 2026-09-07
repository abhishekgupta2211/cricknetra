import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_config.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/theme_provider.dart';
import '../../core/widgets/common.dart';
import '../notifications/notification_providers.dart';

/// Everything that does not need its own tab.
class MoreScreen extends ConsumerWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final unreadMessages = ref.watch(unreadMessagesProvider).valueOrNull ?? 0;
    final unreadNotifs = ref.watch(unreadNotificationsProvider).valueOrNull ?? 0;
    // Resolve from MediaQuery so the icon follows the phone live.
    final palette = resolvePalette(
      ref.watch(themeControllerProvider),
      MediaQuery.platformBrightnessOf(context),
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('More'),
        actions: [
          IconButton(
            tooltip: palette.isDark ? 'Switch to light' : 'Switch to dark',
            icon: Icon(
              palette.isDark ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
              size: 21,
            ),
            onPressed: () =>
                ref.read(themeControllerProvider.notifier).toggleMode(
                      platform: MediaQuery.platformBrightnessOf(context),
                    ),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
        children: [
          CnCard(
            onTap: () => context.push(user == null ? Routes.login : Routes.account),
            child: Row(
              children: [
                // Signed out there is no name to take initials from, and "GU"
                // reads like somebody's actual initials.
                if (user == null)
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: context.cric.surfaceVariant,
                      shape: BoxShape.circle,
                      border: Border.all(color: context.cric.line),
                    ),
                    child: Icon(Icons.person_outline,
                        size: 24, color: context.cric.faint),
                  )
                else
                  CnAvatar(
                    name: user.displayName,
                    size: 48,
                    imageUrl:
                        user.hasPhoto ? ApiConfig.userPhoto(user.id) : null,
                  ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user?.displayName ?? 'Not signed in',
                        style: context.texts.titleSmall,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        user == null
                            ? 'Sign in to score matches and track your career'
                            : '@${user.username} · ${Roles.label(user.role)}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: context.texts.bodySmall,
                      ),
                    ],
                  ),
                ),
                Icon(Icons.chevron_right, size: 20, color: context.cric.faint),
              ],
            ),
          ),
          const SectionHeader(title: 'Cricket'),
          _Group(
            items: [
              (icon: Icons.groups_outlined, label: 'Teams', route: Routes.teams, badge: 0),
              (icon: Icons.person_outline, label: 'Players', route: Routes.players, badge: 0),
              (icon: Icons.place_outlined, label: 'Venues', route: Routes.venues, badge: 0),
              (icon: Icons.leaderboard_outlined, label: 'Leaderboards', route: Routes.leaderboards, badge: 0),
              (icon: Icons.compare_arrows, label: 'Compare', route: Routes.compare, badge: 0),
              (icon: Icons.tune, label: 'Custom rules', route: Routes.rules, badge: 0),
              (icon: Icons.play_circle_outline, label: 'Highlights', route: Routes.highlights, badge: 0),
              (icon: Icons.calculate_outlined, label: 'Tools and calculators', route: Routes.tools, badge: 0),
            ],
          ),
          const SectionHeader(title: 'Community'),
          _Group(
            items: [
              (icon: Icons.dynamic_feed_outlined, label: 'Feed', route: Routes.feed, badge: 0),
              (icon: Icons.people_outline, label: 'Member directory', route: Routes.network, badge: 0),
              (icon: Icons.chat_bubble_outline, label: 'Messages', route: Routes.messages, badge: unreadMessages),
              (icon: Icons.campaign_outlined, label: 'Looking for', route: Routes.lookingFor, badge: 0),
              (icon: Icons.notifications_none, label: 'Notifications', route: Routes.notifications, badge: unreadNotifs),
              (icon: Icons.search, label: 'Search', route: Routes.search, badge: 0),
            ],
          ),
          const SectionHeader(title: 'App'),
          _Group(
            items: [
              // One row for "your own work on competitions", whichever side of
              // one the account is on: an organizer gets their desk, an umpire
              // or commentator the competitions they were appointed to.
              if (user != null && user.can(Caps.createTournament))
                (icon: Icons.event_note_outlined, label: 'Organizer', route: Routes.organizer, badge: 0)
              else if (user != null && Roles.assignmentScoped.contains(user.role))
                (icon: Icons.event_note_outlined, label: 'My assignments', route: Routes.myAssignments, badge: 0),
              (icon: Icons.settings_outlined, label: 'Settings', route: Routes.settings, badge: 0),
              if (user?.isAdmin ?? false)
                (icon: Icons.shield_outlined, label: 'Admin', route: Routes.admin, badge: 0),
            ],
          ),
        ],
      ),
    );
  }
}

class _Group extends StatelessWidget {
  final List<({IconData icon, String label, String route, int badge})> items;

  const _Group({required this.items});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      padding: EdgeInsets.zero,
      child: Column(
        children: [
          for (var i = 0; i < items.length; i++) ...[
            if (i > 0) Divider(height: 1, color: context.cric.line),
            ListTile(
              leading: Icon(items[i].icon, size: 21),
              title: Text(items[i].label, style: context.texts.bodyMedium),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (items[i].badge > 0)
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(
                        color: context.cric.wicket,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        '${items[i].badge}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  const SizedBox(width: 6),
                  Icon(Icons.chevron_right,
                      size: 19, color: context.cric.faint),
                ],
              ),
              onTap: () => context.push(items[i].route),
            ),
          ],
        ],
      ),
    );
  }
}
