import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_service.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/rules.dart';

final presetsProvider = FutureProvider.autoDispose<List<PresetSummary>>(
  (ref) => ref.watch(apiProvider).presets(),
);

/// The full editable rulebook behind a preset — what the builder loads.
final presetRulesProvider =
    FutureProvider.autoDispose.family<MatchRules, String>(
  (ref, formatId) => ref.watch(apiProvider).preset(formatId),
);

final ruleTemplatesProvider = FutureProvider.autoDispose<List<RuleTemplate>>(
  (ref) => ref.watch(apiProvider).ruleTemplates(),
);

final ruleTemplateProvider =
    FutureProvider.autoDispose.family<RuleTemplate, String>(
  (ref, id) => ref.watch(apiProvider).ruleTemplate(id),
);
