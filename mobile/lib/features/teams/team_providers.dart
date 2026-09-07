import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/roster.dart';

final teamsProvider = FutureProvider.autoDispose<List<Team>>(
  (ref) => ref.watch(apiProvider).teams(),
);

final teamProvider = FutureProvider.autoDispose.family<Team, String>(
  (ref, id) => ref.watch(apiProvider).team(id),
);

/// Team record. Null when the server has nothing to report yet.
final teamStatsProvider =
    FutureProvider.autoDispose.family<TeamStats?, String>((ref, id) async {
  try {
    return await ref.watch(apiProvider).teamStats(id);
  } catch (_) {
    return null;
  }
});
