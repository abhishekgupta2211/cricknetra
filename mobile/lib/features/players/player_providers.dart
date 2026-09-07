import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/career.dart';
import '../../core/models/roster.dart';

final playersProvider = FutureProvider.autoDispose<List<Player>>(
  (ref) => ref.watch(apiProvider).players(),
);

final playerStatsProvider =
    FutureProvider.autoDispose.family<PlayerStats, String>(
  (ref, id) => ref.watch(apiProvider).playerStats(id),
);

/// The whole career. Unlike the extras below this is not optional: a profile
/// that cannot load its history should say so rather than quietly show nothing.
final playerHistoryProvider =
    FutureProvider.autoDispose.family<PlayerHistory, String>(
  (ref, id) => ref.watch(apiProvider).playerHistory(id),
);

/// The optional extras on a profile. Each returns null rather than failing the
/// whole screen, because a new player legitimately has none of them.
final playerInsightsProvider =
    FutureProvider.autoDispose.family<PlayerInsights?, String>((ref, id) async {
  try {
    return await ref.watch(apiProvider).playerInsights(id);
  } catch (_) {
    return null;
  }
});

final playerSplitsProvider =
    FutureProvider.autoDispose.family<PlayerSplits?, String>((ref, id) async {
  try {
    return await ref.watch(apiProvider).playerSplits(id);
  } catch (_) {
    return null;
  }
});

final playerAwardsProvider =
    FutureProvider.autoDispose.family<List<PlayerAward>, String>(
        (ref, id) async {
  try {
    return await ref.watch(apiProvider).playerAwards(id);
  } catch (_) {
    return const [];
  }
});

/// Roster profiles matching the signed-in user's mobile number.
final claimablePlayersProvider =
    FutureProvider.autoDispose<List<Player>>((ref) async {
  if (!ref.watch(isSignedInProvider)) return const [];
  try {
    return await ref.watch(apiProvider).claimablePlayers();
  } catch (_) {
    return const [];
  }
});

final myPlayersProvider = FutureProvider.autoDispose<List<Player>>((ref) async {
  if (!ref.watch(isSignedInProvider)) return const [];
  try {
    return await ref.watch(apiProvider).myPlayers();
  } catch (_) {
    return const [];
  }
});

/// A value-equality key for the comparison provider. A plain Map would compare
/// by identity, so every rebuild would create a new provider and refetch.
class ComparePair {
  final String a;
  final String b;

  const ComparePair(this.a, this.b);

  @override
  bool operator ==(Object other) =>
      other is ComparePair && other.a == a && other.b == b;

  @override
  int get hashCode => Object.hash(a, b);
}

final comparePlayersProvider =
    FutureProvider.autoDispose.family<PlayerCompare, ComparePair>(
  (ref, pair) => ref.watch(apiProvider).comparePlayers(pair.a, pair.b),
);
