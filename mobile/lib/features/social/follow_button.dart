import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/social.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';

/// Follow a team, player, tournament or match.
///
/// Renders nothing when signed out or when the follow state cannot be read, so
/// a guest never sees a button that would only bounce them to sign-in.
class FollowButton extends ConsumerStatefulWidget {
  final String entityType;
  final String entityId;

  const FollowButton({
    super.key,
    required this.entityType,
    required this.entityId,
  });

  @override
  ConsumerState<FollowButton> createState() => _FollowButtonState();
}

class _FollowButtonState extends ConsumerState<FollowButton> {
  EntityFollowState? _state;
  bool _busy = false;
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (!ref.read(isSignedInProvider)) return;
    try {
      final s = await ref
          .read(apiProvider)
          .entityFollowState(widget.entityType, widget.entityId);
      if (mounted) setState(() => _state = s);
    } catch (_) {
      if (mounted) setState(() => _failed = true);
    }
  }

  Future<void> _toggle() async {
    final current = _state;
    if (current == null) return;
    setState(() => _busy = true);
    try {
      final api = ref.read(apiProvider);
      final next = current.isFollowing
          ? await api.unfollowEntity(widget.entityType, widget.entityId)
          : await api.followEntity(widget.entityType, widget.entityId);
      if (mounted) setState(() => _state = next);
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!ref.watch(isSignedInProvider) || _failed) {
      return const SizedBox.shrink();
    }
    final s = _state;
    if (s == null) return const SizedBox.shrink();

    return s.isFollowing
        ? OutlinedButton.icon(
            onPressed: _busy ? null : _toggle,
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(0, 38),
              padding: const EdgeInsets.symmetric(horizontal: 14),
              foregroundColor: context.scheme.primary,
            ),
            icon: const Icon(Icons.check, size: 16),
            label: const Text('Following'),
          )
        : ElevatedButton(
            onPressed: _busy ? null : _toggle,
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(0, 38),
              padding: const EdgeInsets.symmetric(horizontal: 16),
            ),
            child: const Text('Follow'),
          );
  }
}

/// Follow another member.
class FollowUserButton extends ConsumerStatefulWidget {
  final String userId;
  final bool initiallyFollowing;

  const FollowUserButton({
    super.key,
    required this.userId,
    required this.initiallyFollowing,
  });

  @override
  ConsumerState<FollowUserButton> createState() => _FollowUserButtonState();
}

class _FollowUserButtonState extends ConsumerState<FollowUserButton> {
  late bool _following = widget.initiallyFollowing;
  bool _busy = false;

  /// The follow list arrives after the first frames, so the parent rebuilds
  /// with the real answer. Without this the button stays frozen on its initial
  /// guess and offers to follow people you already follow.
  @override
  void didUpdateWidget(FollowUserButton old) {
    super.didUpdateWidget(old);
    if (old.initiallyFollowing != widget.initiallyFollowing ||
        old.userId != widget.userId) {
      _following = widget.initiallyFollowing;
    }
  }

  Future<void> _toggle() async {
    setState(() => _busy = true);
    final wasFollowing = _following;
    try {
      final api = ref.read(apiProvider);
      if (wasFollowing) {
        await api.unfollow(widget.userId);
      } else {
        await api.follow(widget.userId);
      }
      if (mounted) setState(() => _following = !wasFollowing);
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return TextButton(
      onPressed: _busy ? null : _toggle,
      style: TextButton.styleFrom(
        visualDensity: VisualDensity.compact,
        foregroundColor:
            _following ? context.cric.muted : context.scheme.primary,
      ),
      child: Text(_following ? 'Following' : 'Follow'),
    );
  }
}
