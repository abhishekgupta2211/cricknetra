import 'dart:async';

import 'package:dio/dio.dart' show CancelToken;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_service.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/match.dart';

final matchesListProvider = FutureProvider.autoDispose<List<MatchSummary>>(
  (ref) => ref.watch(apiProvider).matches(),
);

/// Live matches, resolved to full state so the home hero can show a score.
final liveMatchesProvider =
    FutureProvider.autoDispose<List<MatchState>>((ref) async {
  final api = ref.watch(apiProvider);
  final summaries = await api.matches();
  final live = summaries.where((m) => m.isLive).take(8).toList();
  final states = await Future.wait(
    live.map((m) async {
      try {
        return await api.match(m.id);
      } catch (_) {
        return null;
      }
    }),
  );
  return states.whereType<MatchState>().toList();
});

/// Umpire requests waiting on the signed-in user's approval.
final pendingOfficialsProvider =
    FutureProvider.autoDispose<List<PendingOfficialRequest>>((ref) async {
  if (!ref.watch(isSignedInProvider)) return const [];
  try {
    return await ref.watch(apiProvider).pendingOfficialRequests();
  } catch (_) {
    return const [];
  }
});

/// Everything one match screen needs, in one object.
class MatchSession {
  final MatchState state;

  /// Null when signed out — the officials endpoint needs a token.
  final MatchOfficials? officials;

  const MatchSession({required this.state, this.officials});

  /// Server-computed: admin, or the match owner, or a capability holder, or an
  /// umpire approved for this specific match.
  bool get canScore => officials?.canScore ?? false;

  bool get isManager => officials?.isManager ?? false;
}

/// Loads, refreshes and mutates one match.
///
/// Every scoring call returns the complete new state, so the notifier simply
/// swaps it in — no local score arithmetic anywhere.
class MatchController extends StateNotifier<AsyncValue<MatchSession>> {
  final ApiService api;
  final String matchId;
  final bool signedIn;

  StreamSubscription<void>? _liveSub;
  CancelToken? _liveCancel;
  Timer? _pollTimer;
  bool _refreshing = false;
  bool _disposed = false;

  MatchController({
    required this.api,
    required this.matchId,
    required this.signedIn,
  }) : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    try {
      final session = await _fetch();
      if (_disposed) return;
      state = AsyncValue.data(session);
      _startLive(session.state);
    } catch (e, st) {
      if (_disposed) return;
      state = AsyncValue.error(e, st);
    }
  }

  Future<MatchSession> _fetch() async {
    final matchState = await api.match(matchId);
    MatchOfficials? officials;
    if (signedIn) {
      try {
        officials = await api.matchOfficials(matchId);
      } catch (_) {
        // Not fatal — the screen falls back to read-only.
      }
    }
    return MatchSession(state: matchState, officials: officials);
  }

  /// Re-read the match without flashing a loading state.
  Future<void> refresh() async {
    if (_refreshing || _disposed) return;
    _refreshing = true;
    try {
      final session = await _fetch();
      if (_disposed) return;
      state = AsyncValue.data(session);
      if (session.state.isComplete) _stopLive();
    } catch (_) {
      // Keep showing the last good state.
    } finally {
      _refreshing = false;
    }
  }

  /// Apply a scoring action and swap in the state it returns.
  ///
  /// Errors are rethrown so the caller can show the engine's own sentence — a
  /// 409 means the delivery was illegal and must not be retried.
  Future<void> act(Future<MatchState> Function() action) async {
    final previous = state.value;
    try {
      final newState = await action();
      if (_disposed) return;
      state = AsyncValue.data(
        MatchSession(state: newState, officials: previous?.officials),
      );
      if (newState.isComplete) _stopLive();
    } catch (e) {
      rethrow;
    }
  }

  // ---- live updates

  /// The stream pushes a small frame whenever the score changes; each frame is
  /// a signal to re-fetch, not the state itself.
  void _startLive(MatchState matchState) {
    if (matchState.isComplete || _disposed) return;
    _stopLive();
    _liveCancel = CancelToken();
    _liveSub = api
        .matchStream(matchId, cancelToken: _liveCancel)
        .skip(1) // the first frame is the snapshot we already have
        .listen(
          (event) {
            if (event.event == 'gone') {
              _stopLive();
              return;
            }
            refresh();
          },
          onError: (_) => _fallbackToPolling(),
          onDone: _fallbackToPolling,
          cancelOnError: true,
        );
  }

  /// Some networks and proxies break long-lived streams; polling still works.
  void _fallbackToPolling() {
    if (_disposed) return;
    _liveSub?.cancel();
    _liveSub = null;
    _pollTimer?.cancel();
    if (state.value?.state.isComplete ?? false) return;
    _pollTimer = Timer.periodic(const Duration(seconds: 8), (_) => refresh());
  }

  void _stopLive() {
    _liveSub?.cancel();
    _liveSub = null;
    _liveCancel?.cancel();
    _liveCancel = null;
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  @override
  void dispose() {
    _disposed = true;
    _stopLive();
    super.dispose();
  }
}

final matchControllerProvider = StateNotifierProvider.autoDispose
    .family<MatchController, AsyncValue<MatchSession>, String>((ref, id) {
  return MatchController(
    api: ref.watch(apiProvider),
    matchId: id,
    signedIn: ref.watch(isSignedInProvider),
  );
});

final ballFeedProvider =
    FutureProvider.autoDispose.family<List<BallFeedItem>, String>(
  (ref, id) => ref.watch(apiProvider).ballFeed(id),
);

final matchHighlightsProvider =
    FutureProvider.autoDispose.family<List<HighlightMoment>, String>(
  (ref, id) => ref.watch(apiProvider).matchHighlights(id),
);

final commentaryProvider =
    FutureProvider.autoDispose.family<List<CommentaryNote>, String>(
  (ref, id) => ref.watch(apiProvider).commentary(id),
);

final fieldingProvider =
    FutureProvider.autoDispose.family<List<FieldingEvent>, String>(
  (ref, id) => ref.watch(apiProvider).fieldingEvents(id),
);
