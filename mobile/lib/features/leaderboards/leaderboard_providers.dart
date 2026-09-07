import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/social.dart';

/// Window and location, as a value-equality key so the family caches properly.
class LeaderboardQuery {
  final String window;
  final String? location;

  const LeaderboardQuery({this.window = 'all', this.location});

  @override
  bool operator ==(Object other) =>
      other is LeaderboardQuery &&
      other.window == window &&
      other.location == location;

  @override
  int get hashCode => Object.hash(window, location);
}

final leaderboardQueryProvider =
    StateProvider<LeaderboardQuery>((ref) => const LeaderboardQuery());

final leaderboardsProvider = FutureProvider.autoDispose<Leaderboards>((ref) {
  final q = ref.watch(leaderboardQueryProvider);
  return ref
      .watch(apiProvider)
      .leaderboards(window: q.window, location: q.location);
});
