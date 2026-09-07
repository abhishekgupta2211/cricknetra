import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/org.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/common.dart';
import 'admin_providers.dart';

/// Who changed what, newest first.
///
/// The trail exists to answer one question after the fact — who moved
/// authority or destroyed something — so the lines that do either are flagged
/// rather than left to be spotted in a wall of identical rows.
class AuditScreen extends ConsumerStatefulWidget {
  const AuditScreen({super.key});

  @override
  ConsumerState<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends ConsumerState<AuditScreen> {
  /// Null is every action.
  String? _action;

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);

    // Admin-only. This gate is UX, not security: the server checks the role on
    // the endpoint and refuses whatever the app decides to show.
    if (!auth.isAdmin) {
      return Scaffold(
        appBar: AppBar(title: const Text('Audit trail')),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: GateCard(
            what: 'read the audit trail',
            signedIn: auth.isSignedIn,
            role: auth.user?.role,
            onSignIn: () => context.push(Routes.login),
            onRegister: () => context.push(Routes.register),
          ),
        ),
      );
    }

    final async = ref.watch(auditTrailProvider(_action));

    return Scaffold(
      appBar: AppBar(title: const Text('Audit trail')),
      body: Column(
        children: [
          const SizedBox(height: 8),
          ChipFilterBar<String?>(
            selected: _action,
            onChanged: (v) => setState(() => _action = v),
            options: [
              for (final f in auditActionFilters)
                (value: f.value, label: f.label, count: null),
            ],
          ),
          const SizedBox(height: 8),
          // The list — error and all — renders inside this Scaffold, so a
          // failed load never takes the app bar and its back arrow with it.
          Expanded(
            child: RefreshIndicator(
              onRefresh: () async => ref.invalidate(auditTrailProvider(_action)),
              child: async.when(
                loading: () => const Padding(
                  padding: EdgeInsets.fromLTRB(16, 4, 16, 16),
                  child: ListSkeleton(rows: 4),
                ),
                error: (e, _) => ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    ErrorState(
                      error: e,
                      onRetry: () =>
                          ref.invalidate(auditTrailProvider(_action)),
                    ),
                  ],
                ),
                data: (list) {
                  if (list.isEmpty) {
                    return ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        EmptyState(
                          icon: Icons.history,
                          title: _action == null
                              ? 'Nothing recorded yet'
                              : 'Nothing of that kind yet',
                          message: 'Role grants, organizer changes and '
                              'deletions land here as they happen.',
                        ),
                      ],
                    );
                  }
                  return ListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
                    itemCount: list.length,
                    itemBuilder: (context, i) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _AuditRow(entry: list[i]),
                    ),
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AuditRow extends StatelessWidget {
  final AuditEntry entry;

  const _AuditRow({required this.entry});

  @override
  Widget build(BuildContext context) {
    final weighty = entry.isWeighty;
    final accent = weighty ? context.cric.wicket : context.cric.faint;

    return CnCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      borderColor: weighty ? accent.withValues(alpha: 0.45) : null,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 34,
            height: 34,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: weighty
                  ? context.cric.wicketSoft
                  : context.cric.surfaceVariant,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              weighty ? Icons.gavel_outlined : Icons.history,
              size: 17,
              color: accent,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Wraps rather than sitting in a fixed row: an action label and
                // a badge do not both fit beside each other at 375px.
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      entry.label,
                      style: context.texts.bodyMedium
                          ?.copyWith(fontWeight: FontWeight.w700),
                    ),
                    if (weighty)
                      CnBadge(
                        text: 'Flagged',
                        color: context.cric.wicket,
                        icon: Icons.flag_outlined,
                      ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  [
                    if (entry.actorName.isNotEmpty) entry.actorName,
                    if (entry.resourceType.isNotEmpty)
                      '${entry.resourceType} ${entry.resourceId}'.trim(),
                    if (Fmt.timeAgo(entry.when).isNotEmpty)
                      Fmt.timeAgo(entry.when),
                  ].join(' · '),
                  style: context.texts.labelSmall,
                ),
                if (entry.detail.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(entry.detail, style: context.texts.bodySmall),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
