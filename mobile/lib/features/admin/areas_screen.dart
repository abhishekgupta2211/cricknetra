import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/org.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'admin_providers.dart';

/// The places competitions happen, and the bodies that run them.
///
/// An area is a town; an organization is a body that runs cricket in it. Both
/// exist so an organizer can be posted somewhere specific, which is why the
/// counts are on the card: an area nobody works and nothing happens in is one
/// somebody created by mistake.
class AreasScreen extends ConsumerWidget {
  const AreasScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);

    // Admin-only. This gate is UX, not security: the server checks the role on
    // every one of these endpoints and refuses whatever the app decides to show.
    if (!auth.isAdmin) {
      return Scaffold(
        appBar: AppBar(title: const Text('Areas')),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: GateCard(
            what: 'manage areas and organizations',
            signedIn: auth.isSignedIn,
            role: auth.user?.role,
            onSignIn: () => context.push(Routes.login),
            onRegister: () => context.push(Routes.register),
          ),
        ),
      );
    }

    final areas = ref.watch(areasProvider);
    final orgs = ref.watch(organizationsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Areas & organizations')),
      body: RefreshIndicator(
        onRefresh: () async => invalidateAdminReads(ref),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
          children: [
            Text(
              'An area is a place. An organization is a body that runs cricket '
              'there. An organizer is posted to both.',
              style: context.texts.bodySmall,
            ),
            SectionHeader(
              title: 'Areas',
              trailing: TextButton.icon(
                onPressed: () => _newArea(context, ref),
                icon: const Icon(Icons.add, size: 18),
                label: const Text('New'),
              ),
            ),
            // Rendered inside the Scaffold so a failed load keeps the app bar
            // and its back arrow.
            areas.when(
              loading: () => const ListSkeleton(rows: 2),
              error: (e, _) => ErrorState(
                error: e,
                onRetry: () => ref.invalidate(areasProvider),
              ),
              data: (list) {
                if (list.isEmpty) {
                  return const EmptyState(
                    icon: Icons.place_outlined,
                    title: 'No areas yet',
                    message: 'Add the town or district you run cricket in.',
                  );
                }
                return Column(
                  children: [
                    for (final a in list)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: _AreaCard(
                          area: a,
                          onDelete: () => _deleteArea(context, ref, a),
                        ),
                      ),
                  ],
                );
              },
            ),
            SectionHeader(
              title: 'Organizations',
              trailing: TextButton.icon(
                onPressed: () => _newOrganization(context, ref),
                icon: const Icon(Icons.add, size: 18),
                label: const Text('New'),
              ),
            ),
            orgs.when(
              loading: () => const ListSkeleton(rows: 2),
              error: (e, _) => ErrorState(
                error: e,
                onRetry: () => ref.invalidate(organizationsProvider),
              ),
              data: (list) {
                if (list.isEmpty) {
                  return const EmptyState(
                    icon: Icons.apartment_outlined,
                    title: 'No organizations yet',
                    message: 'Add the club, board or academy that runs the '
                        'competitions.',
                  );
                }
                return Column(
                  children: [
                    for (final o in list)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: CnCard(
                          padding: const EdgeInsets.fromLTRB(16, 12, 8, 12),
                          child: Row(
                            children: [
                              Icon(Icons.apartment_outlined,
                                  size: 20, color: context.cric.faint),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      o.name,
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: context.texts.bodyMedium?.copyWith(
                                          fontWeight: FontWeight.w600),
                                    ),
                                    Text(
                                      o.areaName ?? 'No area',
                                      style: context.texts.labelSmall,
                                    ),
                                  ],
                                ),
                              ),
                              IconButton(
                                tooltip: 'Delete',
                                iconSize: 18,
                                icon: const Icon(Icons.delete_outline),
                                color: context.cric.wicket,
                                onPressed: () =>
                                    _deleteOrganization(context, ref, o),
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
        ),
      ),
    );
  }

  Future<void> _newArea(BuildContext context, WidgetRef ref) async {
    final result = await showModalBottomSheet<({String name, String? state})>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _NewAreaSheet(),
    );
    if (result == null || !context.mounted) return;
    try {
      await ref.read(apiProvider).createArea(result.name, state: result.state);
      if (!context.mounted) return;
      invalidateAdminReads(ref);
      context.toast('Added ${result.name}');
    } catch (e) {
      if (context.mounted) context.toastError(e);
    }
  }

  Future<void> _deleteArea(
      BuildContext context, WidgetRef ref, Area area) async {
    final ok = await confirmDialog(
      context,
      title: 'Delete ${area.name}?',
      message: area.organizers > 0
          ? '${area.organizers} organizer(s) are posted here and would lose '
              'their area.'
          : 'Nothing is posted here.',
    );
    if (!ok || !context.mounted) return;
    try {
      await ref.read(apiProvider).deleteArea(area.id);
      if (!context.mounted) return;
      invalidateAdminReads(ref);
      context.toast('Deleted ${area.name}');
    } catch (e) {
      if (context.mounted) context.toastError(e);
    }
  }

  Future<void> _newOrganization(BuildContext context, WidgetRef ref) async {
    final result = await showModalBottomSheet<({String name, String? areaId})>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _NewOrganizationSheet(),
    );
    if (result == null || !context.mounted) return;
    try {
      await ref
          .read(apiProvider)
          .createOrganization(result.name, areaId: result.areaId);
      if (!context.mounted) return;
      invalidateAdminReads(ref);
      context.toast('Added ${result.name}');
    } catch (e) {
      if (context.mounted) context.toastError(e);
    }
  }

  Future<void> _deleteOrganization(
      BuildContext context, WidgetRef ref, Organization org) async {
    final ok = await confirmDialog(
      context,
      title: 'Delete ${org.name}?',
      message: 'Organizers posted to it lose their organization.',
    );
    if (!ok || !context.mounted) return;
    try {
      await ref.read(apiProvider).deleteOrganization(org.id);
      if (!context.mounted) return;
      invalidateAdminReads(ref);
      context.toast('Deleted ${org.name}');
    } catch (e) {
      if (context.mounted) context.toastError(e);
    }
  }
}

class _AreaCard extends StatelessWidget {
  final Area area;
  final VoidCallback onDelete;

  const _AreaCard({required this.area, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    return CnCard(
      padding: const EdgeInsets.fromLTRB(16, 12, 8, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  area.title,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w700),
                ),
              ),
              IconButton(
                tooltip: 'Delete',
                iconSize: 18,
                icon: const Icon(Icons.delete_outline),
                color: context.cric.wicket,
                onPressed: onDelete,
              ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: StatGrid(
              columns: 2,
              stats: [
                (label: 'Organizers', value: '${area.organizers}'),
                (label: 'Tournaments', value: '${area.tournaments}'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Name plus an optional state, because two towns share a name often enough
/// that the list needs to tell them apart.
class _NewAreaSheet extends StatefulWidget {
  const _NewAreaSheet();

  @override
  State<_NewAreaSheet> createState() => _NewAreaSheetState();
}

class _NewAreaSheetState extends State<_NewAreaSheet> {
  final _name = TextEditingController();
  final _state = TextEditingController();

  @override
  void dispose() {
    _name.dispose();
    _state.dispose();
    super.dispose();
  }

  void _submit() {
    final name = _name.text.trim();
    if (name.isEmpty) {
      context.toast('Name the area');
      return;
    }
    final state = _state.text.trim();
    Navigator.pop(context, (name: name, state: state.isEmpty ? null : state));
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('New area', style: context.texts.titleMedium),
          const SizedBox(height: 16),
          TextField(
            controller: _name,
            autofocus: true,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(
              labelText: 'Area',
              hintText: 'Prayagraj',
              isDense: true,
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _state,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(
              labelText: 'State (optional)',
              hintText: 'Uttar Pradesh',
              isDense: true,
            ),
            onSubmitted: (_) => _submit(),
          ),
          const SizedBox(height: 18),
          ElevatedButton(onPressed: _submit, child: const Text('Add area')),
        ],
      ),
    );
  }
}

/// A body, optionally tied to an area it runs cricket in.
class _NewOrganizationSheet extends ConsumerStatefulWidget {
  const _NewOrganizationSheet();

  @override
  ConsumerState<_NewOrganizationSheet> createState() =>
      _NewOrganizationSheetState();
}

class _NewOrganizationSheetState
    extends ConsumerState<_NewOrganizationSheet> {
  final _name = TextEditingController();
  String? _areaId;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  void _submit() {
    final name = _name.text.trim();
    if (name.isEmpty) {
      context.toast('Name the organization');
      return;
    }
    Navigator.pop(context, (name: name, areaId: _areaId));
  }

  @override
  Widget build(BuildContext context) {
    final areas = ref.watch(areasProvider).valueOrNull ?? const <Area>[];

    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('New organization', style: context.texts.titleMedium),
          const SizedBox(height: 16),
          TextField(
            controller: _name,
            autofocus: true,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(
              labelText: 'Organization',
              hintText: 'XYZ Sports',
              isDense: true,
            ),
            onSubmitted: (_) => _submit(),
          ),
          const SizedBox(height: 14),
          Text('Area', style: context.texts.labelLarge),
          const SizedBox(height: 8),
          DropdownButtonFormField<String?>(
            initialValue: _areaId,
            isExpanded: true,
            decoration: const InputDecoration(isDense: true),
            items: [
              const DropdownMenuItem<String?>(child: Text('No area')),
              for (final a in areas)
                DropdownMenuItem<String?>(
                  value: a.id,
                  child: Text(a.title, overflow: TextOverflow.ellipsis),
                ),
            ],
            onChanged: (v) => setState(() => _areaId = v),
          ),
          const SizedBox(height: 18),
          ElevatedButton(
            onPressed: _submit,
            child: const Text('Add organization'),
          ),
        ],
      ),
    );
  }
}
