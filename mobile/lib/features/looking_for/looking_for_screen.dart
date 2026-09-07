import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/social.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/common.dart';

/// Value-equality key so the filter family caches instead of refetching.
class LookingForQuery {
  final String? kind;
  final String? location;

  const LookingForQuery({this.kind, this.location});

  @override
  bool operator ==(Object other) =>
      other is LookingForQuery &&
      other.kind == kind &&
      other.location == location;

  @override
  int get hashCode => Object.hash(kind, location);
}

final lookingForProvider =
    FutureProvider.autoDispose.family<List<LookingForPost>, LookingForQuery>(
  (ref, q) =>
      ref.watch(apiProvider).lookingFor(kind: q.kind, location: q.location),
);

/// The classifieds board: players looking for a team, teams looking for
/// players, and captains looking for a fixture.
class LookingForScreen extends ConsumerStatefulWidget {
  const LookingForScreen({super.key});

  @override
  ConsumerState<LookingForScreen> createState() => _LookingForScreenState();
}

class _LookingForScreenState extends ConsumerState<LookingForScreen> {
  final _location = TextEditingController();
  Timer? _debounce;
  String? _kind;
  String? _locationFilter;

  @override
  void dispose() {
    _debounce?.cancel();
    _location.dispose();
    super.dispose();
  }

  void _onLocationChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      if (mounted) {
        setState(() => _locationFilter = value.trim().isEmpty ? null : value.trim());
      }
    });
  }

  Future<void> _compose() async {
    final created = await showModalBottomSheet<LookingForPost>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _ComposeSheet(),
    );
    if (created == null || !mounted) return;
    ref.invalidate(lookingForProvider(
      LookingForQuery(kind: _kind, location: _locationFilter),
    ));
    context.toast('Posted');
  }

  @override
  Widget build(BuildContext context) {
    final query = LookingForQuery(kind: _kind, location: _locationFilter);
    final async = ref.watch(lookingForProvider(query));

    return Scaffold(
      appBar: AppBar(title: const Text('Looking for')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _compose,
        icon: const Icon(Icons.add),
        label: const Text('Post'),
      ),
      body: Column(
        children: [
          ChipFilterBar<String?>(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            selected: _kind,
            onChanged: (v) => setState(() => _kind = v),
            options: [
              (value: null, label: 'All', count: null),
              for (final k in LookingForPost.kinds)
                (value: k, label: LookingForPost.kindLabel(k), count: null),
            ],
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
            child: SearchField(
              controller: _location,
              hint: 'Filter by location',
              onChanged: _onLocationChanged,
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
                onRetry: () => ref.invalidate(lookingForProvider(query)),
              ),
              data: (posts) {
                if (posts.isEmpty) {
                  return EmptyState(
                    icon: Icons.campaign_outlined,
                    title: 'Nothing here yet',
                    message: 'Be the first to post a request.',
                    actionLabel: 'Post a request',
                    onAction: _compose,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async =>
                      ref.invalidate(lookingForProvider(query)),
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
                    itemCount: posts.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, i) => _PostCard(
                      post: posts[i],
                      onChanged: () =>
                          ref.invalidate(lookingForProvider(query)),
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

class _PostCard extends ConsumerWidget {
  final LookingForPost post;
  final VoidCallback onChanged;

  const _PostCard({required this.post, required this.onChanged});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CnBadge(text: post.badge),
              if (post.location != null && post.location!.isNotEmpty) ...[
                const SizedBox(width: 8),
                Icon(Icons.place_outlined, size: 13, color: context.cric.faint),
                const SizedBox(width: 3),
                Text(post.location!, style: context.texts.labelSmall),
              ],
              const Spacer(),
              if (post.isClosed)
                CnBadge(text: 'Closed', color: context.cric.faint),
            ],
          ),
          const SizedBox(height: 10),
          Text(post.text, style: context.texts.bodyMedium),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Text(
                  '${post.authorName}'
                  '${post.role == null || post.role!.isEmpty ? '' : ' · ${post.role}'}'
                  ' · ${Fmt.timeAgo(post.when)}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.texts.labelSmall
                      ?.copyWith(color: context.cric.faint),
                ),
              ),
              if (post.mine) ...[
                if (!post.isClosed)
                  TextButton(
                    onPressed: () async {
                      try {
                        await ref
                            .read(apiProvider)
                            .closeLookingFor(post.id);
                        onChanged();
                      } catch (e) {
                        if (context.mounted) context.toastError(e);
                      }
                    },
                    child: const Text('Close'),
                  ),
                IconButton(
                  iconSize: 17,
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () async {
                    final ok = await confirmDialog(
                      context,
                      title: 'Delete this post?',
                      message: 'It disappears from the board.',
                    );
                    if (!ok) return;
                    try {
                      await ref
                          .read(apiProvider)
                          .deleteLookingFor(post.id);
                      onChanged();
                    } catch (e) {
                      if (context.mounted) context.toastError(e);
                    }
                  },
                ),
              ] else
                TextButton.icon(
                  onPressed: () => context.push(Routes.thread(post.authorId)),
                  icon: const Icon(Icons.chat_bubble_outline, size: 15),
                  label: const Text('Message'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ComposeSheet extends ConsumerStatefulWidget {
  const _ComposeSheet();

  @override
  ConsumerState<_ComposeSheet> createState() => _ComposeSheetState();
}

class _ComposeSheetState extends ConsumerState<_ComposeSheet> {
  final _text = TextEditingController();
  final _location = TextEditingController();
  final _role = TextEditingController();
  String _kind = 'team';
  bool _busy = false;

  @override
  void dispose() {
    _text.dispose();
    _location.dispose();
    _role.dispose();
    super.dispose();
  }

  Future<void> _post() async {
    final text = _text.text.trim();
    if (text.isEmpty) {
      context.toast('Say what you are looking for');
      return;
    }
    setState(() => _busy = true);
    try {
      final created = await ref.read(apiProvider).postLookingFor(
            kind: _kind,
            text: text,
            location: _location.text.trim(),
            role: _role.text.trim(),
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
            Text('Post a request', style: context.texts.titleMedium),
            const SizedBox(height: 16),
            Text('I am looking for', style: context.texts.labelLarge),
            const SizedBox(height: 8),
            for (final k in LookingForPost.kinds)
              RadioListTile<String>(
                value: k,
                // ignore: deprecated_member_use
                groupValue: _kind,
                // ignore: deprecated_member_use
                onChanged: (v) => setState(() => _kind = v ?? _kind),
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text(LookingForPost.kindPrompt(k)),
              ),
            const SizedBox(height: 10),
            TextField(
              controller: _text,
              maxLines: 4,
              maxLength: 500,
              decoration: const InputDecoration(
                labelText: 'Details',
                hintText: 'What you need, when, and how to reach you',
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _location,
              decoration: const InputDecoration(
                labelText: 'Location',
                isDense: true,
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _role,
              decoration: const InputDecoration(
                labelText: 'Role (optional)',
                hintText: 'Fast bowler, wicket-keeper, all-rounder',
                isDense: true,
              ),
            ),
            const SizedBox(height: 18),
            ElevatedButton(
              onPressed: _busy ? null : _post,
              child: const Text('Post'),
            ),
          ],
        ),
      ),
    );
  }
}
