import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/social.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_palette.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/theme_provider.dart';
import '../../core/widgets/common.dart';
import '../notifications/notification_providers.dart';

/// Look, notifications and security.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final signedIn = ref.watch(isSignedInProvider);
    final settings = ref.watch(themeControllerProvider);
    // In system mode the stored palette is not necessarily the one on screen,
    // so tick the palette actually being rendered.
    final shownPaletteId =
        resolvePalette(settings, MediaQuery.platformBrightnessOf(context)).id;

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          Text(
            'Pick a look. It applies instantly and is remembered on this device.',
            style: context.texts.bodySmall,
          ),
          const SectionHeader(title: 'Dark'),
          _PaletteGrid(
            palettes: AppPalette.darkPalettes,
            selected: shownPaletteId,
          ),
          const SectionHeader(title: 'Light'),
          _PaletteGrid(
            palettes: AppPalette.lightPalettes,
            selected: shownPaletteId,
          ),
          const SectionHeader(title: 'Follow the system'),
          CnCard(
            child: SwitchListTile(
              value: settings.followsSystem,
              onChanged: (v) => ref.read(themeControllerProvider.notifier).setMode(
                    // Turning it off pins whatever is on screen right now, so
                    // nothing jumps from light to dark under the reader.
                    v
                        ? ThemeMode.system
                        : (MediaQuery.platformBrightnessOf(context) ==
                                Brightness.dark
                            ? ThemeMode.dark
                            : ThemeMode.light),
                  ),
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text('Match the device theme',
                  style: context.texts.bodyMedium),
              subtitle: Text(
                settings.followsSystem
                    ? 'On. The app switches with your phone.'
                    : 'Off. The app stays on the look you picked.',
                style: context.texts.labelSmall,
              ),
            ),
          ),
          if (signedIn) ...[
            const SectionHeader(title: 'Notifications'),
            const _NotificationPrefsCard(),
            const SectionHeader(title: 'Security'),
            CnCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
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
                  const Divider(height: 1),
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(Icons.devices_other,
                        size: 20, color: context.cric.wicket),
                    title: Text(
                      'Sign out everywhere',
                      style: TextStyle(color: context.cric.wicket),
                    ),
                    subtitle: Text(
                      'Revokes every session and forgets push devices',
                      style: context.texts.labelSmall,
                    ),
                    onTap: () async {
                      final ok = await confirmDialog(
                        context,
                        title: 'Sign out on every device?',
                        message:
                            'You will need to sign in again everywhere.',
                        confirmLabel: 'Sign out',
                      );
                      if (!ok) return;
                      try {
                        await ref
                            .read(authControllerProvider.notifier)
                            .logoutEverywhere();
                        if (context.mounted) context.go(Routes.home);
                      } catch (e) {
                        if (context.mounted) context.toastError(e);
                      }
                    },
                  ),
                ],
              ),
            ),
          ],
          const SectionHeader(title: 'About'),
          CnCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('CricNetra', style: context.texts.titleSmall),
                const SizedBox(height: 4),
                Text(
                  'Score your cricket, by your rules. Ball-by-ball scoring, '
                  'career stats, leagues and knockouts.',
                  style: context.texts.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PaletteGrid extends ConsumerWidget {
  final List<AppPalette> palettes;
  final String selected;

  const _PaletteGrid({required this.palettes, required this.selected});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: palettes.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        mainAxisSpacing: 10,
        crossAxisSpacing: 10,
        childAspectRatio: 1.05,
      ),
      itemBuilder: (context, i) {
        final p = palettes[i];
        final isSelected = p.id == selected;
        return InkWell(
          onTap: () =>
              ref.read(themeControllerProvider.notifier).setPalette(p.id),
          borderRadius: BorderRadius.circular(14),
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: p.background,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: isSelected ? p.accent : context.cric.line,
                width: isSelected ? 2 : 1,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // A miniature of the palette in use.
                Container(
                  height: 5,
                  width: 34,
                  decoration: BoxDecoration(
                    color: p.accent,
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
                const SizedBox(height: 7),
                Container(
                  height: 22,
                  decoration: BoxDecoration(
                    color: p.surface,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: p.line),
                  ),
                ),
                const SizedBox(height: 6),
                Container(height: 4, width: 46, color: p.ink),
                const SizedBox(height: 4),
                Container(height: 4, width: 30, color: p.inkMuted),
                const Spacer(),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        p.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: p.ink,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    if (isSelected)
                      Icon(Icons.check_circle, size: 14, color: p.accent),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _NotificationPrefsCard extends ConsumerStatefulWidget {
  const _NotificationPrefsCard();

  @override
  ConsumerState<_NotificationPrefsCard> createState() =>
      _NotificationPrefsCardState();
}

class _NotificationPrefsCardState
    extends ConsumerState<_NotificationPrefsCard> {
  NotificationPrefs? _local;
  bool _saving = false;

  /// Save the whole object; the server ignores keys it does not know.
  Future<void> _save(NotificationPrefs next) async {
    final previous = _local;
    setState(() {
      _local = next;
      _saving = true;
    });
    try {
      final saved = await ref.read(apiProvider).saveNotificationPrefs(
            next.copyWith(
              tzOffset: DateTime.now().timeZoneOffset.inMinutes,
            ),
          );
      if (mounted) setState(() => _local = saved);
    } catch (e) {
      // Put the toggle back where it was.
      if (mounted) {
        setState(() => _local = previous);
        context.toastError(e);
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(notificationPrefsProvider);

    return async.when(
      loading: () => const CnCard(child: SkeletonBox(height: 120)),
      error: (e, _) => CnCard(
        child: ErrorState(
          error: e,
          onRetry: () => ref.invalidate(notificationPrefsProvider),
        ),
      ),
      data: (server) {
        final prefs = _local ?? server;

        Widget toggle(String key, String label, {String? subtitle}) =>
            SwitchListTile(
              value: prefs.byKey(key),
              onChanged:
                  _saving ? null : (v) => _save(prefs.withKey(key, v)),
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(label, style: context.texts.bodyMedium),
              subtitle: subtitle == null
                  ? null
                  : Text(subtitle, style: context.texts.labelSmall),
            );

        return CnCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              toggle('match', 'Live matches'),
              toggle('tournament', 'Tournaments'),
              toggle('team', 'Teams'),
              toggle('player', 'Players'),
              toggle('social', 'Follows and mentions'),
              toggle('achievement', 'Achievements'),
              toggle('system', 'System'),
              toggle('marketing', 'Tips and offers'),
              const Divider(height: 20),
              SwitchListTile(
                value: prefs.pushEnabled,
                onChanged: _saving
                    ? null
                    : (v) => _save(prefs.copyWith(pushEnabled: v)),
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text('Push notifications',
                    style: context.texts.bodyMedium),
              ),
              SwitchListTile(
                value: prefs.emailEnabled,
                onChanged: _saving
                    ? null
                    : (v) => _save(prefs.copyWith(emailEnabled: v)),
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text('Email notifications',
                    style: context.texts.bodyMedium),
              ),
              SwitchListTile(
                value: prefs.sound,
                onChanged:
                    _saving ? null : (v) => _save(prefs.copyWith(sound: v)),
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text('Sound', style: context.texts.bodyMedium),
              ),
              const Divider(height: 20),
              Text('Quiet hours', style: context.texts.labelLarge),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: _HourPicker(
                      label: 'From',
                      enabled: !_saving,
                      value: prefs.quietStart,
                      onChanged: (v) => _save(
                        v == null
                            ? prefs.copyWith(clearQuietStart: true)
                            : prefs.copyWith(quietStart: v),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _HourPicker(
                      label: 'To',
                      enabled: !_saving,
                      value: prefs.quietEnd,
                      onChanged: (v) => _save(
                        v == null
                            ? prefs.copyWith(clearQuietEnd: true)
                            : prefs.copyWith(quietEnd: v),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class _HourPicker extends StatelessWidget {
  final String label;
  final int? value;
  final bool enabled;
  final ValueChanged<int?> onChanged;

  const _HourPicker({
    required this.label,
    required this.value,
    required this.onChanged,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<int?>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label, isDense: true),
      items: [
        const DropdownMenuItem<int?>(value: null, child: Text('Off')),
        for (var h = 0; h < 24; h++)
          DropdownMenuItem<int?>(
            value: h,
            child: Text('${h.toString().padLeft(2, '0')}:00'),
          ),
      ],
      onChanged: enabled ? onChanged : null,
    );
  }
}
