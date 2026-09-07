import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/common.dart';
import 'role_assign_sheet.dart';

final roleRequestsProvider = FutureProvider.autoDispose<List<RoleRequest>>(
  (ref) => ref.watch(apiProvider).roleRequests(),
);

final announcementAnalyticsProvider =
    FutureProvider.autoDispose<List<AnnouncementCampaign>>(
  (ref) => ref.watch(apiProvider).announcementAnalytics(),
);

/// Role approvals and broadcasts.
class AdminScreen extends ConsumerWidget {
  const AdminScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);

    if (!auth.isAdmin) {
      return Scaffold(
        appBar: AppBar(title: const Text('Admin')),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: GateCard(
            what: 'manage role requests',
            signedIn: auth.isSignedIn,
            role: auth.user?.role,
            onSignIn: () => context.push(Routes.login),
            onRegister: () => context.push(Routes.register),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Admin')),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(roleRequestsProvider);
          ref.invalidate(announcementAnalyticsProvider);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
          children: const [
            SectionHeader(
              title: 'Roles and access',
              padding: EdgeInsets.fromLTRB(4, 4, 4, 10),
            ),
            _AdminSectionLinks(),
            _RoleRequests(),
            SectionHeader(title: 'Broadcast an announcement'),
            _BroadcastForm(),
            SectionHeader(title: 'Announcement results'),
            _Analytics(),
          ],
        ),
      ),
    );
  }
}

/// Ways into the rest of the console.
///
/// Organizers, areas and the audit trail get their own routes rather than more
/// sections here: an admin looking for one organizer should not have to scroll
/// past a broadcast form to find them.
class _AdminSectionLinks extends StatelessWidget {
  const _AdminSectionLinks();

  Future<void> _assignRole(BuildContext context) async {
    final result = await showModalBottomSheet<RoleAssignment>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const RoleAssignSheet(),
    );
    if (result == null || !context.mounted) return;
    context.toast(result.summary);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _LinkRow(
          icon: Icons.badge_outlined,
          label: 'Organizers',
          subtitle: 'Post, suspend or remove the people who run competitions',
          onTap: () => context.push(Routes.adminOrganizers),
        ),
        _LinkRow(
          icon: Icons.place_outlined,
          label: 'Areas & organizations',
          subtitle: 'The places and bodies an organizer is posted to',
          onTap: () => context.push(Routes.adminAreas),
        ),
        _LinkRow(
          icon: Icons.history,
          label: 'Audit trail',
          subtitle: 'Who changed what, newest first',
          onTap: () => context.push(Routes.adminAudit),
        ),
        _LinkRow(
          icon: Icons.admin_panel_settings_outlined,
          label: 'Assign a role',
          subtitle: 'Sign-up grants none — this is the only way one is given',
          onTap: () => _assignRole(context),
        ),
      ],
    );
  }
}

class _LinkRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String subtitle;
  final VoidCallback onTap;

  const _LinkRow({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: CnCard(
        onTap: onTap,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: context.cric.accentSoft,
                borderRadius: BorderRadius.circular(11),
              ),
              child: Icon(icon, size: 19, color: context.scheme.primary),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: context.texts.bodyMedium
                        ?.copyWith(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 2),
                  Text(subtitle, style: context.texts.labelSmall),
                ],
              ),
            ),
            Icon(Icons.chevron_right, size: 20, color: context.cric.faint),
          ],
        ),
      ),
    );
  }
}

class _RoleRequests extends ConsumerWidget {
  const _RoleRequests();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(roleRequestsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SectionHeader(
          title: 'Role requests',
          padding: EdgeInsets.fromLTRB(4, 4, 4, 10),
        ),
        async.when(
          loading: () => const ListSkeleton(rows: 2),
          error: (e, _) => ErrorState(
            error: e,
            onRetry: () => ref.invalidate(roleRequestsProvider),
          ),
          data: (list) {
            if (list.isEmpty) {
              return CnCard(
                child: Text('No pending requests.',
                    style: context.texts.bodySmall),
              );
            }
            return Column(
              children: [
                for (final r in list)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: CnCard(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 12),
                      child: Row(
                        children: [
                          CnAvatar(name: r.fullName, size: 38),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  r.fullName,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: context.texts.bodyMedium
                                      ?.copyWith(fontWeight: FontWeight.w600),
                                ),
                                Text(
                                  '@${r.username} · wants ${Roles.label(r.requestedRole)}',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: context.texts.labelSmall,
                                ),
                              ],
                            ),
                          ),
                          TextButton(
                            onPressed: () async {
                              try {
                                await ref
                                    .read(apiProvider)
                                    .approveRole(r.userId);
                                ref.invalidate(roleRequestsProvider);
                                if (context.mounted) {
                                  context.toast('Approved');
                                }
                              } catch (e) {
                                if (context.mounted) context.toastError(e);
                              }
                            },
                            child: const Text('Approve'),
                          ),
                          IconButton(
                            iconSize: 18,
                            icon: const Icon(Icons.close),
                            onPressed: () async {
                              try {
                                await ref
                                    .read(apiProvider)
                                    .rejectRole(r.userId);
                                ref.invalidate(roleRequestsProvider);
                              } catch (e) {
                                if (context.mounted) context.toastError(e);
                              }
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _BroadcastForm extends ConsumerStatefulWidget {
  const _BroadcastForm();

  @override
  ConsumerState<_BroadcastForm> createState() => _BroadcastFormState();
}

class _BroadcastFormState extends ConsumerState<_BroadcastForm> {
  final _title = TextEditingController();
  final _text = TextEditingController();
  final _link = TextEditingController();
  String _category = 'system';
  bool _busy = false;

  @override
  void dispose() {
    _title.dispose();
    _text.dispose();
    _link.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final title = _title.text.trim();
    final text = _text.text.trim();
    if (title.isEmpty || text.isEmpty) {
      context.toast('A broadcast needs a title and a message');
      return;
    }
    final ok = await confirmDialog(
      context,
      title: 'Send to everyone?',
      message: _category == 'system'
          ? 'This reaches every active account.'
          : 'This reaches accounts that opted in to tips and offers.',
      confirmLabel: 'Send',
      destructive: false,
    );
    if (!ok || !mounted) return;

    setState(() => _busy = true);
    try {
      final result = await ref.read(apiProvider).sendAnnouncement(
            title: title,
            text: text,
            category: _category,
            link: _link.text.trim(),
          );
      _title.clear();
      _text.clear();
      _link.clear();
      ref.invalidate(announcementAnalyticsProvider);
      if (!mounted) return;
      context.toast('Sent to ${result.recipients} people');
    } catch (e) {
      if (!mounted) return;
      context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _title,
            maxLength: 120,
            decoration: const InputDecoration(
              labelText: 'Title',
              isDense: true,
              counterText: '',
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _text,
            maxLines: 3,
            maxLength: 255,
            decoration: const InputDecoration(labelText: 'Message'),
          ),
          const SizedBox(height: 6),
          CnSegmented<String>(
            selected: _category,
            onChanged: (v) => setState(() => _category = v),
            options: const [
              (value: 'system', label: 'Everyone'),
              (value: 'marketing', label: 'Opted in only'),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _link,
            decoration: const InputDecoration(
              labelText: 'Link (optional)',
              hintText: '/t/5',
              isDense: true,
            ),
          ),
          const SizedBox(height: 14),
          ElevatedButton.icon(
            onPressed: _busy ? null : _send,
            icon: const Icon(Icons.campaign_outlined, size: 19),
            label: const Text('Broadcast'),
          ),
        ],
      ),
    );
  }
}

class _Analytics extends ConsumerWidget {
  const _Analytics();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(announcementAnalyticsProvider);

    return async.when(
      loading: () => const ListSkeleton(rows: 2),
      error: (e, _) => ErrorState(
        error: e,
        onRetry: () => ref.invalidate(announcementAnalyticsProvider),
      ),
      data: (list) {
        if (list.isEmpty) {
          return CnCard(
            child: Text('No announcements sent yet.',
                style: context.texts.bodySmall),
          );
        }
        return Column(
          children: [
            for (final c in list)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: CnCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              c.title,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: context.texts.bodyMedium
                                  ?.copyWith(fontWeight: FontWeight.w700),
                            ),
                          ),
                          CnBadge(
                            text: Fmt.percent(c.ctr, places: 0),
                            color: context.scheme.primary,
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(c.text, style: context.texts.bodySmall),
                      const SizedBox(height: 10),
                      StatGrid(
                        columns: 4,
                        stats: [
                          (label: 'Sent', value: '${c.recipients}'),
                          (label: 'Delivered', value: '${c.delivered}'),
                          (label: 'Opened', value: '${c.opened}'),
                          (label: 'Clicked', value: '${c.clicked}'),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}
