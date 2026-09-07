import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/tournament.dart';

final tournamentsProvider =
    FutureProvider.autoDispose<List<TournamentSummary>>(
  (ref) => ref.watch(apiProvider).tournaments(),
);

final tournamentProvider =
    FutureProvider.autoDispose.family<Tournament, String>(
  (ref, id) => ref.watch(apiProvider).tournament(id),
);

final tournamentSquadsProvider =
    FutureProvider.autoDispose.family<List<TeamSquad>, String>(
        (ref, id) async {
  try {
    return await ref.watch(apiProvider).tournamentSquads(id);
  } catch (_) {
    return const [];
  }
});
