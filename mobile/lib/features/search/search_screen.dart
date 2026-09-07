import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/social.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../network/network_screen.dart';
import '../notifications/notification_providers.dart';
import '../players/players_list_screen.dart';
import '../teams/teams_list_screen.dart';
import '../venues/venues_screen.dart';

/// One search across players, teams, tournaments, members and venues.
///
/// Members only come back when signed in, which is why the hint appears for
/// guests rather than an empty section.
class SearchScreen extends ConsumerStatefulWidget {
  final String? initialQuery;

  const SearchScreen({super.key, this.initialQuery});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  late final TextEditingController _controller =
      TextEditingController(text: widget.initialQuery ?? '');

  Timer? _debounce;
  SearchResults? _results;
  Object? _error;
  bool _searching = false;

  /// Guards against a slow early response overwriting a newer one.
  int _sequence = 0;

  @override
  void initState() {
    super.initState();
    if ((widget.initialQuery ?? '').trim().isNotEmpty) {
      _run(widget.initialQuery!);
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _onChanged(String value) {
    _debounce?.cancel();
    if (value.trim().isEmpty) {
      setState(() {
        _results = null;
        _error = null;
        _searching = false;
      });
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 250), () => _run(value));
  }

  Future<void> _run(String query) async {
    final seq = ++_sequence;
    setState(() {
      _searching = true;
      _error = null;
    });
    try {
      final results = await ref.read(apiProvider).search(query.trim());
      if (!mounted || seq != _sequence) return;
      setState(() {
        _results = results;
        _searching = false;
      });
    } catch (e) {
      if (!mounted || seq != _sequence) return;
      setState(() {
        _error = e;
        _searching = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final signedIn = ref.watch(isSignedInProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Search')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
            child: SearchField(
              controller: _controller,
              hint: 'Players, teams, tournaments, grounds',
              autofocus: widget.initialQuery == null,
              onChanged: _onChanged,
            ),
          ),
          if (!signedIn)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
              child: Text(
                'Sign in to find members too.',
                style: context.texts.labelSmall
                    ?.copyWith(color: context.cric.faint),
              ),
            ),
          Expanded(child: _body()),
        ],
      ),
    );
  }

  Widget _body() {
    if (_error != null) {
      return ErrorState(
        error: _error!,
        onRetry: () => _run(_controller.text),
      );
    }
    if (_searching && _results == null) {
      return const Padding(
        padding: EdgeInsets.symmetric(horizontal: 16),
        child: ListSkeleton(rows: 3),
      );
    }
    final me = ref.watch(currentUserProvider);
    final following = ref.watch(followingProvider).valueOrNull ?? const <String>{};
    final r = _results;
    if (r == null) {
      return const EmptyState(
        icon: Icons.search,
        title: 'Type a name to search',
      );
    }
    if (r.isEmpty) {
      return EmptyState(
        icon: Icons.search_off,
        title: 'No matches for "${r.query}"',
      );
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
      children: [
        if (r.players.isNotEmpty) ...[
          const SectionHeader(title: 'Players'),
          for (final p in r.players)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: PlayerRow(player: p),
            ),
        ],
        if (r.teams.isNotEmpty) ...[
          const SectionHeader(title: 'Teams'),
          for (final t in r.teams)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: TeamRow(team: t),
            ),
        ],
        if (r.tournaments.isNotEmpty) ...[
          const SectionHeader(title: 'Tournaments'),
          for (final t in r.tournaments)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: CnCard(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                onTap: () => context.push(Routes.tournament(t.id)),
                child: Row(
                  children: [
                    Icon(Icons.emoji_events_outlined,
                        size: 20, color: context.cric.amber),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(t.name,
                              style: context.texts.bodyMedium
                                  ?.copyWith(fontWeight: FontWeight.w600)),
                          Text(t.subtitle, style: context.texts.bodySmall),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
        if (r.members.isNotEmpty) ...[
          const SectionHeader(title: 'Members'),
          for (final m in r.members)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: MemberRow(
                key: ValueKey(m.id),
                member: m,
                isMe: m.id == me?.id,
                isFollowing: following.contains(m.id),
              ),
            ),
        ],
        if (r.venues.isNotEmpty) ...[
          const SectionHeader(title: 'Grounds and academies'),
          for (final v in r.venues)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: VenueRow(venue: v),
            ),
        ],
      ],
    );
  }
}
