import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'rule_providers.dart';

/// The built-in formats and the rulebooks you have saved.
///
/// A rulebook here is data, not code: the same scoring engine plays box
/// cricket, gully cricket and a T20 by reading different settings.
class RuleTemplatesScreen extends ConsumerWidget {
  const RuleTemplatesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final presets = ref.watch(presetsProvider);
    final templates = ref.watch(ruleTemplatesProvider);
    final canManage = ref.watch(authControllerProvider).can(Caps.manageRules);

    return Scaffold(
      appBar: AppBar(title: const Text('Custom rules')),
      floatingActionButton: canManage
          ? FloatingActionButton.extended(
              onPressed: () => context.push(Routes.ruleBuilder),
              icon: const Icon(Icons.add),
              label: const Text('New rulebook'),
            )
          : null,
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(presetsProvider);
          ref.invalidate(ruleTemplatesProvider);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
          children: [
            Text(
              'The rulebook is data, not code. The same engine plays box '
              'cricket, gully cricket and a T20 by reading different settings.',
              style: context.texts.bodySmall,
            ),
            const SectionHeader(title: 'Built-in formats'),
            presets.when(
              loading: () => const ListSkeleton(rows: 3),
              error: (e, _) => ErrorState(
                error: e,
                onRetry: () => ref.invalidate(presetsProvider),
              ),
              data: (list) => Column(
                children: [
                  for (final p in list)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: CnCard(
                        onTap: canManage
                            ? () => context.push(
                                '${Routes.ruleBuilder}?from=preset:${p.id}')
                            : null,
                        child: Row(
                          children: [
                            Container(
                              width: 40,
                              height: 40,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                color: context.cric.accentSoft,
                                borderRadius: BorderRadius.circular(11),
                              ),
                              child: Icon(Icons.tune,
                                  size: 19, color: context.scheme.primary),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(p.name,
                                      style: context.texts.bodyMedium?.copyWith(
                                          fontWeight: FontWeight.w600)),
                                  const SizedBox(height: 2),
                                  Text(p.summaryLine,
                                      style: context.texts.bodySmall),
                                ],
                              ),
                            ),
                            if (canManage)
                              Text('Customise',
                                  style: context.texts.labelSmall?.copyWith(
                                      color: context.scheme.primary)),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SectionHeader(title: 'Your rulebooks'),
            templates.when(
              loading: () => const ListSkeleton(rows: 2),
              error: (e, _) => ErrorState(
                error: e,
                onRetry: () => ref.invalidate(ruleTemplatesProvider),
              ),
              data: (list) {
                if (list.isEmpty) {
                  return EmptyState(
                    icon: Icons.rule_outlined,
                    title: 'No saved rulebooks',
                    message: canManage
                        ? 'Build one and reuse it for every match in your league.'
                        : 'Organizers can save custom rulebooks here.',
                    actionLabel: canManage ? 'Build a rulebook' : null,
                    onAction: canManage
                        ? () => context.push(Routes.ruleBuilder)
                        : null,
                  );
                }
                return Column(
                  children: [
                    for (final t in list)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: CnCard(
                          onTap: canManage
                              ? () => context.push(
                                  '${Routes.ruleBuilder}?from=template:${t.id}')
                              : null,
                          child: Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(t.name,
                                        style: context.texts.bodyMedium
                                            ?.copyWith(
                                                fontWeight: FontWeight.w600)),
                                    const SizedBox(height: 2),
                                    Text(t.summary,
                                        style: context.texts.bodySmall),
                                  ],
                                ),
                              ),
                              if (ref.watch(authControllerProvider).isAdmin)
                                IconButton(
                                  iconSize: 18,
                                  icon: const Icon(Icons.delete_outline),
                                  onPressed: () async {
                                    final ok = await confirmDialog(
                                      context,
                                      title: 'Delete this rulebook?',
                                      message:
                                          'Matches already played with it keep '
                                          'their own copy.',
                                    );
                                    if (!ok) return;
                                    try {
                                      await ref
                                          .read(apiProvider)
                                          .deleteRuleTemplate(t.id);
                                      ref.invalidate(ruleTemplatesProvider);
                                    } catch (e) {
                                      if (context.mounted) {
                                        context.toastError(e);
                                      }
                                    }
                                  },
                                ),
                            ],
                          ),
                        ),
                      ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
