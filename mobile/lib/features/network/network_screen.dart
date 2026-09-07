import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_config.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../notifications/notification_providers.dart';
import '../social/follow_button.dart';
import '../teams/team_providers.dart';
import '../teams/teams_list_screen.dart';

/// Members by role, plus teams — the directory of everyone in the network.
final directoryProvider =
    FutureProvider.autoDispose.family<List<PublicUser>, String>(
  (ref, role) => ref.watch(apiProvider).users(role: role),
);

class NetworkScreen extends ConsumerStatefulWidget {
  /// True when pushed as its own page rather than shown in the tab shell.
  final bool standalone;

  const NetworkScreen({super.key, this.standalone = false});

  @override
  ConsumerState<NetworkScreen> createState() => _NetworkScreenState();
}

class _NetworkScreenState extends ConsumerState<NetworkScreen> {
  String _tab = Roles.player;

  static const _teamsTab = '__teams__';

  @override
  Widget build(BuildContext context) {
    final signedIn = ref.watch(isSignedInProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Community'),
        automaticallyImplyLeading: widget.standalone,
        actions: [
          IconButton(
            tooltip: 'Search',
            icon: const Icon(Icons.search, size: 22),
            onPressed: () => context.push(Routes.search),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: Column(
        children: [
          // Icon above label, so "Looking for" cannot wrap mid-word on a
          // narrow phone the way a side-by-side icon and label does.
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            child: Row(
              children: const [
                Expanded(
                  child: _QuickAction(
                    icon: Icons.dynamic_feed_outlined,
                    label: 'Feed',
                    route: Routes.feed,
                  ),
                ),
                SizedBox(width: 8),
                Expanded(
                  child: _QuickAction(
                    icon: Icons.campaign_outlined,
                    label: 'Looking for',
                    route: Routes.lookingFor,
                  ),
                ),
                SizedBox(width: 8),
                Expanded(
                  child: _QuickAction(
                    icon: Icons.chat_bubble_outline,
                    label: 'Messages',
                    route: Routes.messages,
                  ),
                ),
              ],
            ),
          ),
          ChipFilterBar<String>(
            selected: _tab,
            onChanged: (v) => setState(() => _tab = v),
            options: [
              for (final r in Roles.directoryRoles)
                (value: r, label: Roles.plural(r), count: null),
              (value: _teamsTab, label: 'Teams', count: null),
            ],
          ),
          const SizedBox(height: 10),
          Expanded(
            child: !signedIn
                // A ListView keeps the card sized to its content instead of
                // stretching it down the whole screen.
                ? ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      GateCard(
                        what: 'browse players, umpires and commentators',
                        signedIn: false,
                        onSignIn: () => context.push(Routes.login),
                        onRegister: () => context.push(Routes.register),
                      ),
                    ],
                  )
                : _tab == _teamsTab
                    ? _teamsList()
                    : _membersList(_tab),
          ),
        ],
      ),
    );
  }

  Widget _teamsList() {
    final async = ref.watch(teamsProvider);
    return async.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(horizontal: 16),
        child: ListSkeleton(),
      ),
      error: (e, _) => ErrorState(
        error: e,
        onRetry: () => ref.invalidate(teamsProvider),
      ),
      data: (list) => list.isEmpty
          ? const EmptyState(
              icon: Icons.groups_outlined,
              title: 'No teams yet',
            )
          : ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
              itemCount: list.length,
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (context, i) => TeamRow(team: list[i]),
            ),
    );
  }

  Widget _membersList(String role) {
    final async = ref.watch(directoryProvider(role));
    final following = ref.watch(followingProvider).valueOrNull ?? const <String>{};
    final me = ref.watch(currentUserProvider);

    return async.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(horizontal: 16),
        child: ListSkeleton(),
      ),
      error: (e, _) => ErrorState(
        error: e,
        onRetry: () => ref.invalidate(directoryProvider(role)),
      ),
      data: (list) => list.isEmpty
          ? EmptyState(
              icon: Icons.person_search_outlined,
              title: 'No ${Roles.plural(role).toLowerCase()} yet',
            )
          : RefreshIndicator(
              onRefresh: () async => ref.invalidate(directoryProvider(role)),
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
                itemCount: list.length,
                separatorBuilder: (_, _) => const SizedBox(height: 10),
                itemBuilder: (context, i) => MemberRow(
                  key: ValueKey(list[i].id),
                  member: list[i],
                  isMe: list[i].id == me?.id,
                  isFollowing: following.contains(list[i].id),
                ),
              ),
            ),
    );
  }
}

/// A compact icon-over-label shortcut, sized to survive a 375px screen.
class _QuickAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final String route;

  const _QuickAction({
    required this.icon,
    required this.label,
    required this.route,
  });

  @override
  Widget build(BuildContext context) {
    return CnCard(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
      onTap: () => context.push(route),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 19, color: context.scheme.primary),
          const SizedBox(height: 5),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: context.texts.labelSmall?.copyWith(
              fontWeight: FontWeight.w600,
              fontSize: 11.5,
            ),
          ),
        ],
      ),
    );
  }
}

class MemberRow extends StatelessWidget {
  final PublicUser member;
  final bool isMe;
  final bool isFollowing;

  const MemberRow({
    super.key,
    required this.member,
    this.isMe = false,
    this.isFollowing = false,
  });

  @override
  Widget build(BuildContext context) {
    return CnCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          CnAvatar(
            name: member.fullName,
            size: 42,
            imageUrl:
                member.hasPhoto ? ApiConfig.userPhoto(member.id) : null,
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
                        member.fullName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: context.texts.bodyMedium
                            ?.copyWith(fontWeight: FontWeight.w600),
                      ),
                    ),
                    if (member.isVerified) ...[
                      const SizedBox(width: 5),
                      Icon(Icons.verified,
                          size: 14, color: context.scheme.primary),
                    ],
                  ],
                ),
                const SizedBox(height: 1),
                Text(
                  member.handleLine,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.labelSmall,
                ),
                Text(
                  member.recordLine,
                  style: context.texts.labelSmall
                      ?.copyWith(color: context.cric.faint),
                ),
              ],
            ),
          ),
          if (!isMe) ...[
            FollowUserButton(
              userId: member.id,
              initiallyFollowing: isFollowing,
            ),
            IconButton(
              iconSize: 18,
              visualDensity: VisualDensity.compact,
              tooltip: 'Message',
              icon: const Icon(Icons.chat_bubble_outline),
              onPressed: () => context.push(Routes.thread(member.id)),
            ),
            if (member.mobileNo.isNotEmpty)
              IconButton(
                iconSize: 18,
                visualDensity: VisualDensity.compact,
                tooltip: 'Call',
                icon: const Icon(Icons.call_outlined),
                onPressed: () =>
                    launchUrl(Uri.parse('tel:${member.mobileNo}')),
              ),
          ],
        ],
      ),
    );
  }
}
