import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/social.dart';
import '../../core/models/user.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';

class VenueQuery {
  final String? kind;
  final String? q;

  const VenueQuery({this.kind, this.q});

  @override
  bool operator ==(Object other) =>
      other is VenueQuery && other.kind == kind && other.q == q;

  @override
  int get hashCode => Object.hash(kind, q);
}

final venuesProvider =
    FutureProvider.autoDispose.family<List<Venue>, VenueQuery>(
  (ref, query) => ref.watch(apiProvider).venues(kind: query.kind, q: query.q),
);

/// Grounds and coaching academies.
class VenuesScreen extends ConsumerStatefulWidget {
  const VenuesScreen({super.key});

  @override
  ConsumerState<VenuesScreen> createState() => _VenuesScreenState();
}

class _VenuesScreenState extends ConsumerState<VenuesScreen> {
  final _search = TextEditingController();
  Timer? _debounce;
  String? _kind;
  String? _query;

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  void _onSearch(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 250), () {
      if (mounted) {
        setState(() => _query = value.trim().isEmpty ? null : value.trim());
      }
    });
  }

  Future<void> _add() async {
    final created = await showModalBottomSheet<Venue>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _VenueFormSheet(),
    );
    if (created == null || !mounted) return;
    ref.invalidate(venuesProvider(VenueQuery(kind: _kind, q: _query)));
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    final query = VenueQuery(kind: _kind, q: _query);
    final async = ref.watch(venuesProvider(query));

    return Scaffold(
      appBar: AppBar(title: const Text('Venues')),
      floatingActionButton: auth.can(Caps.createTeam)
          ? FloatingActionButton.extended(
              onPressed: _add,
              icon: const Icon(Icons.add),
              label: const Text('Add venue'),
            )
          : null,
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
            child: Column(
              children: [
                SearchField(
                  controller: _search,
                  hint: 'Search grounds and academies',
                  onChanged: _onSearch,
                ),
                const SizedBox(height: 10),
                CnSegmented<String?>(
                  selected: _kind,
                  onChanged: (v) => setState(() => _kind = v),
                  options: const [
                    (value: null, label: 'All'),
                    (value: 'ground', label: 'Grounds'),
                    (value: 'academy', label: 'Academies'),
                  ],
                ),
              ],
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
                onRetry: () => ref.invalidate(venuesProvider(query)),
              ),
              data: (list) {
                if (list.isEmpty) {
                  return EmptyState(
                    icon: Icons.place_outlined,
                    title: 'No venues yet',
                    message:
                        'Add the grounds and academies your league plays at.',
                    actionLabel:
                        auth.can(Caps.createTeam) ? 'Add a venue' : null,
                    onAction: auth.can(Caps.createTeam) ? _add : null,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async =>
                      ref.invalidate(venuesProvider(query)),
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
                    itemCount: list.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, i) => VenueRow(
                      venue: list[i],
                      canDelete: auth.isAdmin,
                      onDeleted: () =>
                          ref.invalidate(venuesProvider(query)),
                    ),
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

class VenueRow extends ConsumerWidget {
  final Venue venue;
  final bool canDelete;
  final VoidCallback? onDeleted;

  const VenueRow({
    super.key,
    required this.venue,
    this.canDelete = false,
    this.onDeleted,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return CnCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: context.cric.surfaceVariant,
              borderRadius: BorderRadius.circular(11),
            ),
            child: Icon(
              venue.isAcademy ? Icons.school_outlined : Icons.place_outlined,
              size: 19,
              color: context.scheme.primary,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  venue.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 2),
                Text(
                  venue.subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.bodySmall,
                ),
                if (venue.note != null && venue.note!.isNotEmpty)
                  Text(
                    venue.note!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.texts.labelSmall
                        ?.copyWith(color: context.cric.faint),
                  ),
              ],
            ),
          ),
          if (venue.contact != null && venue.contact!.isNotEmpty)
            IconButton(
              iconSize: 18,
              visualDensity: VisualDensity.compact,
              tooltip: 'Call',
              icon: const Icon(Icons.call_outlined),
              onPressed: () => launchUrl(Uri.parse('tel:${venue.contact}')),
            ),
          if (canDelete)
            IconButton(
              iconSize: 18,
              visualDensity: VisualDensity.compact,
              icon: const Icon(Icons.delete_outline),
              onPressed: () async {
                final ok = await confirmDialog(
                  context,
                  title: 'Remove this venue?',
                  message: venue.name,
                  confirmLabel: 'Remove',
                );
                if (!ok) return;
                try {
                  await ref.read(apiProvider).deleteVenue(venue.id);
                  onDeleted?.call();
                } catch (e) {
                  if (context.mounted) context.toastError(e);
                }
              },
            )
          else
            CnBadge(
              text: Venue.kindLabel(venue.kind),
              color: context.cric.muted,
            ),
        ],
      ),
    );
  }
}

class _VenueFormSheet extends ConsumerStatefulWidget {
  const _VenueFormSheet();

  @override
  ConsumerState<_VenueFormSheet> createState() => _VenueFormSheetState();
}

class _VenueFormSheetState extends ConsumerState<_VenueFormSheet> {
  final _name = TextEditingController();
  final _city = TextEditingController();
  final _address = TextEditingController();
  final _contact = TextEditingController();
  final _note = TextEditingController();
  String _kind = 'ground';
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _city.dispose();
    _address.dispose();
    _contact.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final name = _name.text.trim();
    if (name.isEmpty) {
      context.toast('Name the venue');
      return;
    }
    setState(() => _busy = true);
    try {
      final created = await ref.read(apiProvider).createVenue(
            name: name,
            kind: _kind,
            city: _city.text.trim(),
            address: _address.text.trim(),
            contact: _contact.text.trim(),
            note: _note.text.trim(),
          );
      if (!mounted) return;
      Navigator.pop(context, created);
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
            Text('Add a venue', style: context.texts.titleMedium),
            const SizedBox(height: 16),
            CnSegmented<String>(
              selected: _kind,
              onChanged: (v) => setState(() => _kind = v),
              options: const [
                (value: 'ground', label: 'Ground'),
                (value: 'academy', label: 'Academy'),
              ],
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _name,
              textCapitalization: TextCapitalization.words,
              decoration:
                  const InputDecoration(labelText: 'Name', isDense: true),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _city,
              decoration:
                  const InputDecoration(labelText: 'City', isDense: true),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _address,
              decoration:
                  const InputDecoration(labelText: 'Address', isDense: true),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _contact,
              keyboardType: TextInputType.phone,
              decoration:
                  const InputDecoration(labelText: 'Contact', isDense: true),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _note,
              maxLength: 300,
              decoration: const InputDecoration(
                labelText: 'Note',
                hintText: 'Pitch type, nets, floodlights',
                isDense: true,
              ),
            ),
            const SizedBox(height: 14),
            ElevatedButton(
              onPressed: _busy ? null : _save,
              child: const Text('Add venue'),
            ),
          ],
        ),
      ),
    );
  }
}
