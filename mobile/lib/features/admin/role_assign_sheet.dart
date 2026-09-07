import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_config.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/user.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'admin_providers.dart';

/// What the sheet granted, handed back so the caller can say what happened
/// without re-reading the account.
class RoleAssignment {
  final PublicUser user;
  final String role;

  const RoleAssignment({required this.user, required this.role});

  /// "Rahul Yadav is now Organizer"
  String get summary => '${user.displayLabel} is now ${Roles.label(role)}';
}

extension on PublicUser {
  /// A name to show, falling back to the handle for accounts with none.
  String get displayLabel => fullName.isNotEmpty ? fullName : username;
}

/// Grant a role.
///
/// Sign-up hands out no role at all — every account is created as a general
/// user — so this sheet is the only place authority is given. It says as much
/// on screen, because an admin who does not know that goes looking for a
/// setting on the sign-up form that no longer exists.
///
/// Pops a [RoleAssignment] on success, or nothing when dismissed.
class RoleAssignSheet extends ConsumerStatefulWidget {
  /// The account to act on. Null opens the picker first, for the entry point
  /// that starts from "somebody needs a role" rather than from a person.
  final PublicUser? user;

  const RoleAssignSheet({super.key, this.user});

  @override
  ConsumerState<RoleAssignSheet> createState() => _RoleAssignSheetState();
}

class _RoleAssignSheetState extends ConsumerState<RoleAssignSheet> {
  PublicUser? _picked;
  String? _role;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _picked = widget.user;
    _role = widget.user?.role;
  }

  Future<void> _assign() async {
    final user = _picked;
    final role = _role;
    if (user == null || role == null) return;

    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).assignRole(user.id, role);
      if (!mounted) return;
      Navigator.pop(context, RoleAssignment(user: user, role: role));
    } catch (e) {
      if (!mounted) return;
      context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final picked = _picked;

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.9,
      builder: (context, controller) => ListView(
        controller: controller,
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 12,
          bottom: MediaQuery.of(context).viewInsets.bottom + 24,
        ),
        children: [
          Text('Assign a role', style: context.texts.titleMedium),
          const SizedBox(height: 6),
          Text(
            'Sign-up grants no role — every account starts as a general user. '
            'Assigning it here is the only way a role is given.',
            style: context.texts.bodySmall,
          ),
          const SizedBox(height: 16),
          if (picked == null)
            AdminUserPicker(
              onPicked: (u) => setState(() {
                _picked = u;
                _role = u.role;
              }),
            )
          else ...[
            CnCard(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(
                children: [
                  CnAvatar(
                    name: picked.displayLabel,
                    size: 38,
                    imageUrl:
                        picked.hasPhoto ? ApiConfig.userPhoto(picked.id) : null,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          picked.displayLabel,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: context.texts.bodyMedium
                              ?.copyWith(fontWeight: FontWeight.w600),
                        ),
                        Text(
                          '@${picked.username} · now ${Roles.label(picked.role)}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: context.texts.labelSmall,
                        ),
                      ],
                    ),
                  ),
                  // Only offered when the sheet opened without a person, so a
                  // row-level "assign a role" cannot silently retarget.
                  if (widget.user == null)
                    TextButton(
                      onPressed: _busy
                          ? null
                          : () => setState(() {
                                _picked = null;
                                _role = null;
                              }),
                      child: const Text('Change'),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Text('Role', style: context.texts.labelLarge),
            const SizedBox(height: 8),
            for (final role in assignableRoles)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _RoleOption(
                  role: role,
                  selected: role == _role,
                  onTap: () => setState(() => _role = role),
                ),
              ),
            const SizedBox(height: 14),
            ElevatedButton(
              onPressed: _busy || _role == null || _role == picked.role
                  ? null
                  : _assign,
              child: Text(
                _role == null || _role == picked.role
                    ? 'Pick a different role'
                    : 'Assign ${Roles.label(_role!)}',
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _RoleOption extends StatelessWidget {
  final String role;
  final bool selected;
  final VoidCallback onTap;

  const _RoleOption({
    required this.role,
    required this.selected,
    required this.onTap,
  });

  /// [Roles.blurb] speaks to somebody choosing for themselves at sign-up and
  /// says nothing at all for admin, so the console explains the two that
  /// matter most to the person granting them.
  String get _blurb => switch (role) {
        Roles.admin => 'Full access, including these screens.',
        Roles.generalUser => 'Follow matches and browse. No write access.',
        _ => Roles.blurb(role).replaceAll(' Needs admin approval.', ''),
      };

  @override
  Widget build(BuildContext context) {
    return CnCard(
      onTap: onTap,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      borderColor: selected ? context.scheme.primary : null,
      color: selected ? context.cric.accentSoft : null,
      child: Row(
        children: [
          Icon(
            selected ? Icons.check_circle : Icons.circle_outlined,
            size: 20,
            color: selected ? context.scheme.primary : context.cric.faint,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  Roles.label(role),
                  style: context.texts.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
                if (_blurb.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(_blurb, style: context.texts.labelSmall),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// A searchable list of existing accounts.
///
/// Both admin flows — granting a role and posting an organizer — act on an
/// account that already exists, so they search the same directory instead of
/// offering a second way to create a login with its own password rules.
class AdminUserPicker extends ConsumerStatefulWidget {
  final ValueChanged<PublicUser> onPicked;
  final String hint;

  const AdminUserPicker({
    super.key,
    required this.onPicked,
    this.hint = 'Search by name, handle or number',
  });

  @override
  ConsumerState<AdminUserPicker> createState() => _AdminUserPickerState();
}

class _AdminUserPickerState extends ConsumerState<AdminUserPicker> {
  final _search = TextEditingController();
  String _query = '';

  /// The picker lives inside a scrolling sheet, so every match would be built
  /// at once. Showing the first handful and asking for a narrower search keeps
  /// a large directory from janking the sheet open.
  static const _maxShown = 25;

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  List<PublicUser> _matching(List<PublicUser> all) {
    final q = _query.trim().toLowerCase();
    if (q.isEmpty) return all;
    return [
      for (final u in all)
        if (u.fullName.toLowerCase().contains(q) ||
            u.username.toLowerCase().contains(q) ||
            u.mobileNo.contains(q) ||
            u.userCode.toLowerCase().contains(q))
          u,
    ];
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(allUsersProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SearchField(
          controller: _search,
          hint: widget.hint,
          onChanged: (v) => setState(() => _query = v),
        ),
        const SizedBox(height: 12),
        async.when(
          loading: () => const ListSkeleton(rows: 3),
          error: (e, _) => ErrorState(
            error: e,
            onRetry: () => ref.invalidate(allUsersProvider),
          ),
          data: (all) {
            final matches = _matching(all);
            if (matches.isEmpty) {
              return EmptyState(
                icon: Icons.person_search_outlined,
                title: all.isEmpty ? 'No accounts yet' : 'Nobody matches that',
                message: all.isEmpty
                    ? 'People sign up themselves; you grant the role afterwards.'
                    : 'Try a handle or a mobile number.',
              );
            }
            final shown = matches.take(_maxShown).toList();
            return Column(
              children: [
                for (final u in shown)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: CnCard(
                      onTap: () => widget.onPicked(u),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 10),
                      child: Row(
                        children: [
                          CnAvatar(
                            name: u.displayLabel,
                            size: 36,
                            imageUrl:
                                u.hasPhoto ? ApiConfig.userPhoto(u.id) : null,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  u.displayLabel,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: context.texts.bodyMedium
                                      ?.copyWith(fontWeight: FontWeight.w600),
                                ),
                                Text(
                                  '@${u.username} · ${Roles.label(u.role)}',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: context.texts.labelSmall,
                                ),
                              ],
                            ),
                          ),
                          Icon(Icons.chevron_right,
                              size: 20, color: context.cric.faint),
                        ],
                      ),
                    ),
                  ),
                if (matches.length > shown.length)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      '${matches.length - shown.length} more — narrow the search',
                      style: context.texts.labelSmall,
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}
