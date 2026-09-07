import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/org.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'admin_providers.dart';
import 'role_assign_sheet.dart';

/// Who runs competitions, and where.
///
/// An organizer is an existing account plus a posting: an area and an
/// organization. The two ways to end one are deliberately kept apart on this
/// screen — suspending stands somebody down for a season while they keep the
/// role, removing demotes the account outright — because they read as the same
/// button and are not the same act.
class OrganizersScreen extends ConsumerStatefulWidget {
  const OrganizersScreen({super.key});

  @override
  ConsumerState<OrganizersScreen> createState() => _OrganizersScreenState();
}

class _OrganizersScreenState extends ConsumerState<OrganizersScreen> {
  /// Null is every area.
  String? _areaId;

  Future<void> _postOrganizer({Organizer? existing}) async {
    final saved = await showModalBottomSheet<Organizer>(
      context: context,
      isScrollControlled: true,
      builder: (context) => _PostingSheet(existing: existing),
    );
    if (saved == null || !mounted) return;
    invalidateAdminReads(ref);
    context.toast(existing == null
        ? '${saved.displayName} is now an organizer'
        : 'Moved ${saved.displayName} to ${saved.posting}');
  }

  /// Suspending keeps the role and the tournaments; it only stops them acting.
  Future<void> _setActive(Organizer o, bool active) async {
    if (active == false) {
      final ok = await confirmDialog(
        context,
        title: 'Suspend ${o.displayName}?',
        message: 'They keep the organizer role and their '
            '${o.tournaments} tournament(s), but cannot create or run anything '
            'until you restore them.',
        confirmLabel: 'Suspend',
        destructive: false,
      );
      if (!ok || !mounted) return;
    }
    try {
      await ref.read(apiProvider).updateOrganizer(o.userId, isActive: active);
      if (!mounted) return;
      invalidateAdminReads(ref);
      context.toast(active
          ? '${o.displayName} can act again'
          : '${o.displayName} is suspended — the role is untouched');
    } catch (e) {
      if (mounted) context.toastError(e);
    }
  }

  /// Removing is the heavier of the two: the account drops to a general user.
  Future<void> _remove(Organizer o) async {
    final ok = await confirmDialog(
      context,
      title: 'Remove ${o.displayName}?',
      message: 'This demotes the account to a general user — not the same as '
          'suspending, which keeps the role. Their ${o.tournaments} '
          'tournament(s) stay owned by them, to reassign or delete deliberately.',
      confirmLabel: 'Remove and demote',
    );
    if (!ok || !mounted) return;
    try {
      await ref.read(apiProvider).removeOrganizer(o.userId);
      if (!mounted) return;
      invalidateAdminReads(ref);
      context.toast('${o.displayName} is a general user again');
    } catch (e) {
      if (mounted) context.toastError(e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);

    // Admin-only. This gate is UX, not security: the server checks the role on
    // every one of these endpoints and refuses whatever the app decides to show.
    if (!auth.isAdmin) {
      return Scaffold(
        appBar: AppBar(title: const Text('Organizers')),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: GateCard(
            what: 'manage organizers',
            signedIn: auth.isSignedIn,
            role: auth.user?.role,
            onSignIn: () => context.push(Routes.login),
            onRegister: () => context.push(Routes.register),
          ),
        ),
      );
    }

    final areas = ref.watch(areasProvider).valueOrNull ?? const <Area>[];
    final async = ref.watch(organizersProvider(_areaId));

    return Scaffold(
      appBar: AppBar(title: const Text('Organizers')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _postOrganizer,
        icon: const Icon(Icons.person_add_alt),
        label: const Text('Add organizer'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => invalidateAdminReads(ref),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
          children: [
            const _SuspendVersusRemove(),
            if (areas.isNotEmpty) ...[
              const SizedBox(height: 14),
              ChipFilterBar<String?>(
                padding: EdgeInsets.zero,
                selected: _areaId,
                onChanged: (v) => setState(() => _areaId = v),
                options: [
                  (value: null, label: 'All areas', count: null),
                  for (final a in areas)
                    (value: a.id, label: a.name, count: a.organizers),
                ],
              ),
            ],
            const SizedBox(height: 14),
            // The error renders here, inside the Scaffold, so the app bar and
            // its back arrow survive a failed load.
            async.when(
              loading: () => const ListSkeleton(rows: 3),
              error: (e, _) => ErrorState(
                error: e,
                onRetry: () => ref.invalidate(organizersProvider(_areaId)),
              ),
              data: (list) {
                if (list.isEmpty) {
                  return EmptyState(
                    icon: Icons.badge_outlined,
                    title: 'No organizers here',
                    message: 'Pick an account that already exists and post them '
                        'to an area and an organization.',
                    actionLabel: 'Add organizer',
                    onAction: _postOrganizer,
                  );
                }
                return Column(
                  children: [
                    for (final o in list)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _OrganizerCard(
                          organizer: o,
                          onEdit: () => _postOrganizer(existing: o),
                          onSuspend: () => _setActive(o, !o.isActive),
                          onRemove: () => _remove(o),
                        ),
                      ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

/// The difference spelled out once, above the list, rather than hoped for in
/// two button labels.
class _SuspendVersusRemove extends StatelessWidget {
  const _SuspendVersusRemove();

  @override
  Widget build(BuildContext context) {
    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _line(
            context,
            icon: Icons.pause_circle_outline,
            color: context.cric.amber,
            title: 'Suspend',
            body: 'Stops them acting. Keeps the organizer role and their '
                'tournaments, so a season off is reversible.',
          ),
          const SizedBox(height: 12),
          _line(
            context,
            icon: Icons.person_remove_outlined,
            color: context.cric.wicket,
            title: 'Remove',
            body: 'Demotes the account to a general user. Tournaments they own '
                'stay theirs until you reassign or delete them.',
          ),
        ],
      ),
    );
  }

  Widget _line(
    BuildContext context, {
    required IconData icon,
    required Color color,
    required String title,
    required String body,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 18, color: color),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: context.texts.bodyMedium
                    ?.copyWith(fontWeight: FontWeight.w700, color: color),
              ),
              const SizedBox(height: 2),
              Text(body, style: context.texts.bodySmall),
            ],
          ),
        ),
      ],
    );
  }
}

class _OrganizerCard extends StatelessWidget {
  final Organizer organizer;
  final VoidCallback onEdit;
  final VoidCallback onSuspend;
  final VoidCallback onRemove;

  const _OrganizerCard({
    required this.organizer,
    required this.onEdit,
    required this.onSuspend,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    final o = organizer;

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              CnAvatar(name: o.displayName, size: 40),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      o.displayName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.texts.bodyMedium
                          ?.copyWith(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      o.posting.isEmpty ? '@${o.username}' : o.posting,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.texts.labelSmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              CnBadge(
                text: o.isActive ? 'Active' : 'Suspended',
                color: o.isActive ? context.scheme.primary : context.cric.amber,
                icon: o.isActive
                    ? Icons.check_circle_outline
                    : Icons.pause_circle_outline,
              ),
            ],
          ),
          const SizedBox(height: 14),
          // A wrapping grid, not a row of Expanded fields: an organization
          // name and an area name both need more than a quarter of 375px.
          StatGrid(
            columns: 3,
            valueMaxLines: 2,
            stats: [
              (label: 'Area', value: o.areaName ?? '—'),
              (label: 'Organization', value: o.organizationName ?? '—'),
              (label: 'Tournaments', value: '${o.tournaments}'),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 4,
            children: [
              TextButton.icon(
                onPressed: onEdit,
                icon: const Icon(Icons.edit_location_alt_outlined, size: 17),
                label: const Text('Edit posting'),
              ),
              TextButton.icon(
                onPressed: onSuspend,
                style: TextButton.styleFrom(
                    foregroundColor:
                        o.isActive ? context.cric.amber : context.scheme.primary),
                icon: Icon(
                  o.isActive
                      ? Icons.pause_circle_outline
                      : Icons.play_circle_outline,
                  size: 17,
                ),
                label: Text(o.isActive ? 'Suspend' : 'Restore'),
              ),
              TextButton.icon(
                onPressed: onRemove,
                style:
                    TextButton.styleFrom(foregroundColor: context.cric.wicket),
                icon: const Icon(Icons.person_remove_outlined, size: 17),
                label: const Text('Remove'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Post somebody as an organizer, or move an existing one.
///
/// Creating starts from an account that already exists: there is one sign-up,
/// one password policy and one verification flow, and this is not a second way
/// in. Editing skips the picker because moving somebody's area should never be
/// able to land on the wrong person.
class _PostingSheet extends ConsumerStatefulWidget {
  final Organizer? existing;

  const _PostingSheet({this.existing});

  @override
  ConsumerState<_PostingSheet> createState() => _PostingSheetState();
}

class _PostingSheetState extends ConsumerState<_PostingSheet> {
  PublicUser? _user;
  String? _areaId;
  String? _organizationId;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _areaId = widget.existing?.areaId;
    _organizationId = widget.existing?.organizationId;
  }

  bool get _isEdit => widget.existing != null;

  /// Accounts are allowed to have no full name, so fall back to the handle
  /// rather than showing a blank avatar.
  String get _name {
    final existing = widget.existing;
    if (existing != null) return existing.displayName;
    final u = _user;
    if (u == null) return '';
    return u.fullName.isNotEmpty ? u.fullName : u.username;
  }

  Future<void> _save() async {
    final userId = widget.existing?.userId ?? _user?.id;
    if (userId == null) return;
    if (_areaId == null && _organizationId == null) {
      context.toast('Pick an area or an organization');
      return;
    }

    setState(() => _busy = true);
    try {
      final api = ref.read(apiProvider);
      final saved = _isEdit
          ? await api.updateOrganizer(
              userId,
              areaId: _areaId,
              organizationId: _organizationId,
            )
          : await api.createOrganizer(
              userId,
              areaId: _areaId,
              organizationId: _organizationId,
            );
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
    final areas = ref.watch(areasProvider).valueOrNull ?? const <Area>[];
    final orgs =
        ref.watch(organizationsProvider).valueOrNull ?? const <Organization>[];
    // An organization belongs to an area, so once an area is chosen the list
    // narrows — picking a body from another town is always a mistake.
    final orgChoices = _areaId == null
        ? orgs
        : [
            for (final o in orgs)
              if (o.areaId == null || o.areaId == _areaId) o,
          ];
    final needsUser = !_isEdit && _user == null;

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.9,
      builder: (context, controller) => ListView(
        controller: controller,
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 12,
          bottom: MediaQuery.of(context).viewInsets.bottom + 24,
        ),
        children: [
          Text(
            _isEdit ? 'Edit posting' : 'Add an organizer',
            style: context.texts.titleMedium,
          ),
          const SizedBox(height: 6),
          Text(
            _isEdit
                ? 'Move ${widget.existing!.displayName} to another area or body.'
                : 'Pick an account that already exists. Signing up never grants '
                    'the role; you do, here.',
            style: context.texts.bodySmall,
          ),
          const SizedBox(height: 16),
          if (needsUser)
            AdminUserPicker(onPicked: (u) => setState(() => _user = u))
          else ...[
            CnCard(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(
                children: [
                  CnAvatar(name: _name, size: 36),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      _name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.texts.bodyMedium
                          ?.copyWith(fontWeight: FontWeight.w600),
                    ),
                  ),
                  if (!_isEdit)
                    TextButton(
                      onPressed:
                          _busy ? null : () => setState(() => _user = null),
                      child: const Text('Change'),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Text('Area', style: context.texts.labelLarge),
            const SizedBox(height: 8),
            DropdownButtonFormField<String?>(
              initialValue: _areaId,
              isExpanded: true,
              decoration: const InputDecoration(isDense: true),
              items: [
                const DropdownMenuItem<String?>(
                  child: Text('No area'),
                ),
                for (final a in areas)
                  DropdownMenuItem<String?>(
                    value: a.id,
                    child: Text(a.title, overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: (v) => setState(() {
                _areaId = v;
                // A body from the old area would no longer belong here.
                if (v != null &&
                    orgs.any((o) =>
                        o.id == _organizationId &&
                        o.areaId != null &&
                        o.areaId != v)) {
                  _organizationId = null;
                }
              }),
            ),
            const SizedBox(height: 14),
            Text('Organization', style: context.texts.labelLarge),
            const SizedBox(height: 8),
            DropdownButtonFormField<String?>(
              initialValue: _organizationId,
              isExpanded: true,
              decoration: const InputDecoration(isDense: true),
              items: [
                const DropdownMenuItem<String?>(
                  child: Text('No organization'),
                ),
                for (final o in orgChoices)
                  DropdownMenuItem<String?>(
                    value: o.id,
                    child: Text(o.name, overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: (v) => setState(() => _organizationId = v),
            ),
            if (areas.isEmpty && orgs.isEmpty) ...[
              const SizedBox(height: 10),
              Text(
                'No areas or organizations exist yet — create one first.',
                style: context.texts.labelSmall
                    ?.copyWith(color: context.cric.amber),
              ),
            ],
            const SizedBox(height: 18),
            ElevatedButton(
              onPressed: _busy ? null : _save,
              child: Text(_isEdit ? 'Save posting' : 'Make organizer'),
            ),
          ],
        ],
      ),
    );
  }
}
