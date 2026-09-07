import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api/api_config.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../players/player_providers.dart';
import '../players/players_list_screen.dart';

/// Your account: identity, verification, records, photo and claimed profiles.
class AccountScreen extends ConsumerStatefulWidget {
  const AccountScreen({super.key});

  @override
  ConsumerState<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends ConsumerState<AccountScreen> {
  /// Bumped after a photo change to defeat the image cache.
  int _photoBust = 0;
  bool _busy = false;

  Future<void> _pickPhoto() async {
    try {
      final file = await ImagePicker().pickImage(
        source: ImageSource.gallery,
        maxWidth: 1200,
        imageQuality: 88,
      );
      if (file == null || !mounted) return;
      setState(() => _busy = true);
      await ref.read(apiProvider).uploadProfilePhoto(file.path);
      await ref.read(authControllerProvider.notifier).refreshUser();
      if (!mounted) return;
      setState(() => _photoBust = DateTime.now().millisecondsSinceEpoch);
      context.toast('Photo updated');
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _removePhoto() async {
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).deleteProfilePhoto();
      await ref.read(authControllerProvider.notifier).refreshUser();
      if (!mounted) return;
      setState(() => _photoBust = DateTime.now().millisecondsSinceEpoch);
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    if (user == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Account')),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: GateCard(
            what: 'see your account',
            signedIn: false,
            onSignIn: () => context.push(Routes.login),
            onRegister: () => context.push(Routes.register),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Account'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined, size: 21),
            tooltip: 'Settings',
            onPressed: () => context.push(Routes.settings),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          if (user.rolePending)
            Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: CnCard(
                color: context.cric.amberSoft,
                borderColor: context.cric.amber.withValues(alpha: 0.3),
                child: Row(
                  children: [
                    Icon(Icons.hourglass_empty,
                        size: 18, color: context.cric.amber),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        '${Roles.label(user.requestedRole ?? '')} role is '
                        'waiting for an admin to approve it.',
                        style: context.texts.bodySmall,
                      ),
                    ),
                  ],
                ),
              ),
            ),

          // Identity
          CnCard(
            child: Row(
              children: [
                Stack(
                  children: [
                    CnAvatar(
                      name: user.displayName,
                      size: 62,
                      imageUrl: user.hasPhoto
                          ? ApiConfig.userPhoto(user.id, bust: _photoBust)
                          : null,
                    ),
                    Positioned(
                      right: 0,
                      bottom: 0,
                      child: InkWell(
                        onTap: _busy ? null : _pickPhoto,
                        child: Container(
                          padding: const EdgeInsets.all(4),
                          decoration: BoxDecoration(
                            color: context.scheme.primary,
                            shape: BoxShape.circle,
                            border: Border.all(
                                color: context.scheme.surface, width: 2),
                          ),
                          child: Icon(Icons.camera_alt,
                              size: 12, color: context.scheme.onPrimary),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              user.fullName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: context.texts.titleMedium,
                            ),
                          ),
                          if (user.isVerified) ...[
                            const SizedBox(width: 6),
                            Icon(Icons.verified,
                                size: 15, color: context.scheme.primary),
                          ],
                        ],
                      ),
                      Text(
                        '@${user.username} · ${Roles.label(user.role)}',
                        style: context.texts.bodySmall,
                      ),
                      Text(
                        '${user.userCode} · ${user.mobileNo}',
                        style: context.texts.labelSmall
                            ?.copyWith(color: context.cric.faint),
                      ),
                    ],
                  ),
                ),
                if (user.hasPhoto)
                  IconButton(
                    iconSize: 18,
                    tooltip: 'Remove photo',
                    icon: const Icon(Icons.delete_outline),
                    onPressed: _busy ? null : _removePhoto,
                  ),
              ],
            ),
          ),

          if (!user.isVerified) ...[
            const SizedBox(height: 14),
            const _VerifyCard(),
          ],

          const SectionHeader(title: 'Your records'),
          CnCard(
            child: StatGrid(
              columns: 5,
              stats: [
                (label: 'Scored', value: '${user.records.matchesScored}'),
                (label: 'Umpired', value: '${user.records.matchesUmpired}'),
                (
                  label: 'Comm.',
                  value: '${user.records.matchesCommentated}'
                ),
                (
                  label: 'Cups',
                  value: '${user.records.tournamentsOrganized}'
                ),
                (label: 'Teams', value: '${user.records.teamsOwned}'),
              ],
            ),
          ),

          const SectionHeader(title: 'What your role can do'),
          CnCard(
            child: user.capabilities.isEmpty
                ? Text(
                    'View-only access. You can browse everything and follow '
                    'players and teams.',
                    style: context.texts.bodySmall,
                  )
                : Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      for (final c in user.capabilities)
                        CnBadge(text: Caps.label(c)),
                    ],
                  ),
          ),

          const _MyProfilesCard(),

          const SectionHeader(title: 'Account'),
          CnCard(
            child: Column(
              children: [
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.mail_outline, size: 20),
                  title: const Text('Email'),
                  subtitle: Text(user.email ?? 'Not set'),
                  trailing: const Icon(Icons.chevron_right, size: 18),
                  onTap: () async {
                    final email = await promptDialog(
                      context,
                      title: 'Email address',
                      hint: 'you@example.com',
                      initial: user.email ?? '',
                      keyboardType: TextInputType.emailAddress,
                    );
                    if (email == null) return;
                    try {
                      await ref.read(apiProvider).setEmail(email);
                      await ref
                          .read(authControllerProvider.notifier)
                          .refreshUser();
                      if (context.mounted) context.toast('Email saved');
                    } catch (e) {
                      if (context.mounted) context.toastError(e);
                    }
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.home_outlined, size: 20),
                  title: const Text('Address and location'),
                  trailing: const Icon(Icons.chevron_right, size: 18),
                  onTap: () => context.push(Routes.profileDetails),
                ),
                if (user.isAdmin) ...[
                  const Divider(height: 1),
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.shield_outlined, size: 20),
                    title: const Text('Admin'),
                    trailing: const Icon(Icons.chevron_right, size: 18),
                    onTap: () => context.push(Routes.admin),
                  ),
                ],
                const Divider(height: 1),
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.logout, size: 20),
                  title: const Text('Sign out'),
                  onTap: () async {
                    await ref.read(authControllerProvider.notifier).logout();
                    if (context.mounted) context.go(Routes.home);
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Mobile verification by one-time code.
class _VerifyCard extends ConsumerStatefulWidget {
  const _VerifyCard();

  @override
  ConsumerState<_VerifyCard> createState() => _VerifyCardState();
}

class _VerifyCardState extends ConsumerState<_VerifyCard> {
  final _code = TextEditingController();
  bool _sent = false;
  bool _busy = false;
  String? _devCode;

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _request() async {
    setState(() => _busy = true);
    try {
      final dev = await ref.read(apiProvider).requestVerification();
      if (!mounted) return;
      setState(() {
        _sent = true;
        _devCode = dev;
        // Dev builds hand the code back so testing needs no SMS provider.
        if (dev != null) _code.text = dev;
      });
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _confirm() async {
    final code = _code.text.trim();
    if (code.length < 4) {
      context.toast('Enter the code you received');
      return;
    }
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).confirmVerification(code);
      await ref.read(authControllerProvider.notifier).refreshUser();
      ref.invalidate(claimablePlayersProvider);
      if (mounted) context.toast('Mobile verified');
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(Icons.verified_outlined,
                  size: 18, color: context.cric.amber),
              const SizedBox(width: 8),
              Text('Verify your mobile', style: context.texts.titleSmall),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Verifying lets you claim your player profile and its career stats.',
            style: context.texts.bodySmall,
          ),
          const SizedBox(height: 12),
          if (!_sent)
            ElevatedButton(
              onPressed: _busy ? null : _request,
              child: const Text('Send code'),
            )
          else ...[
            TextField(
              controller: _code,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Verification code',
                isDense: true,
              ),
            ),
            if (_devCode != null)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  'Development build: the code is filled in for you.',
                  style: context.texts.labelSmall
                      ?.copyWith(color: context.cric.faint),
                ),
              ),
            const SizedBox(height: 10),
            ElevatedButton(
              onPressed: _busy ? null : _confirm,
              child: const Text('Confirm'),
            ),
          ],
        ],
      ),
    );
  }
}

/// Roster profiles you have claimed, and any that match your number.
class _MyProfilesCard extends ConsumerWidget {
  const _MyProfilesCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mine = ref.watch(myPlayersProvider).valueOrNull ?? const [];
    final claimable = ref.watch(claimablePlayersProvider).valueOrNull ?? const [];
    if (mine.isEmpty && claimable.isEmpty) return const SizedBox.shrink();

    final user = ref.watch(currentUserProvider);

    return Column(
      children: [
        const SectionHeader(title: 'Your cricket profiles'),
        for (final p in mine)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: PlayerRow(player: p),
          ),
        if (claimable.isNotEmpty) ...[
          CnCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'These roster profiles match your number',
                  style: context.texts.titleSmall,
                ),
                const SizedBox(height: 8),
                for (final p in claimable)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 5),
                    child: Row(
                      children: [
                        CnAvatar(name: p.name, size: 32),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(p.name, style: context.texts.bodyMedium),
                        ),
                        if (user?.isVerified ?? false)
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              minimumSize: const Size(0, 34),
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 14),
                            ),
                            onPressed: () async {
                              try {
                                await ref
                                    .read(apiProvider)
                                    .claimPlayer(p.id);
                                ref.invalidate(myPlayersProvider);
                                ref.invalidate(claimablePlayersProvider);
                                if (context.mounted) {
                                  context.toast('Profile claimed');
                                }
                              } catch (e) {
                                if (context.mounted) context.toastError(e);
                              }
                            },
                            child: const Text('Claim'),
                          )
                        else
                          Text(
                            'Verify first',
                            style: context.texts.labelSmall
                                ?.copyWith(color: context.cric.faint),
                          ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}
