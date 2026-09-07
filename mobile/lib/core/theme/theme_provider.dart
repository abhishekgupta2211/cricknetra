import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app_palette.dart';

/// The chosen look, remembered on the device.
///
/// Mirrors the website's behaviour: a light and a dark palette are remembered
/// separately, so toggling between modes returns to the palette you last used
/// in that mode rather than resetting.
class ThemeSettings {
  /// The palette last chosen, whichever side it was on.
  final String paletteId;

  /// The palette to use on each side. Following the system means switching
  /// between these two as the phone changes, so both have to be remembered —
  /// picking Sand for day and Ocean for night must survive sunrise.
  final String? darkPaletteId;
  final String? lightPaletteId;

  /// Defaults to following the phone, so a fresh install matches whatever the
  /// person already has their device set to.
  final ThemeMode mode;

  const ThemeSettings({
    this.paletteId = 'emerald',
    this.darkPaletteId,
    this.lightPaletteId,
    this.mode = ThemeMode.system,
  });

  AppPalette get palette => AppPalette.byId(paletteId);

  bool get followsSystem => mode == ThemeMode.system;

  /// The palette to show on each side, preferring the one last used there and
  /// falling back to the current pick, then to the default pair.
  AppPalette get darkCounterpart {
    if (darkPaletteId != null) return AppPalette.byId(darkPaletteId!);
    return palette.isDark ? palette : AppPalette.emerald;
  }

  AppPalette get lightCounterpart {
    if (lightPaletteId != null) return AppPalette.byId(lightPaletteId!);
    return palette.isDark ? AppPalette.emeraldLight : palette;
  }

  ThemeSettings copyWith({
    String? paletteId,
    String? darkPaletteId,
    String? lightPaletteId,
    ThemeMode? mode,
  }) =>
      ThemeSettings(
        paletteId: paletteId ?? this.paletteId,
        darkPaletteId: darkPaletteId ?? this.darkPaletteId,
        lightPaletteId: lightPaletteId ?? this.lightPaletteId,
        mode: mode ?? this.mode,
      );
}

class ThemeController extends StateNotifier<ThemeSettings> {
  static const _paletteKey = 'cn_theme_palette';
  static const _modeKey = 'cn_theme_mode';
  static const _lastDarkKey = 'cn_theme_last_dark';
  static const _lastLightKey = 'cn_theme_last_light';

  ThemeController() : super(const ThemeSettings()) {
    _load();
  }

  SharedPreferences? _prefs;

  Future<void> _load() async {
    try {
      _prefs = await SharedPreferences.getInstance();
      final id = _prefs?.getString(_paletteKey);
      final modeName = _prefs?.getString(_modeKey);
      state = ThemeSettings(
        paletteId: id ?? 'emerald',
        darkPaletteId: _prefs?.getString(_lastDarkKey),
        lightPaletteId: _prefs?.getString(_lastLightKey),
        mode: _modeFromName(modeName),
      );
    } catch (_) {
      // Preferences are unavailable; the defaults still work.
    }
  }

  /// An unset preference means the person has never chosen, so follow the
  /// phone rather than imposing dark.
  static ThemeMode _modeFromName(String? name) => switch (name) {
        'light' => ThemeMode.light,
        'dark' => ThemeMode.dark,
        _ => ThemeMode.system,
      };

  static String _modeName(ThemeMode m) => switch (m) {
        ThemeMode.light => 'light',
        ThemeMode.system => 'system',
        ThemeMode.dark => 'dark',
      };

  /// Pick a specific palette. Choosing a light palette also switches the app
  /// into light mode, which is what a person tapping a light swatch expects.
  Future<void> setPalette(String id) async {
    final p = AppPalette.byId(id);
    final mode = p.isDark ? ThemeMode.dark : ThemeMode.light;
    state = state.copyWith(
      paletteId: id,
      mode: mode,
      darkPaletteId: p.isDark ? id : null,
      lightPaletteId: p.isDark ? null : id,
    );
    await _prefs?.setString(_paletteKey, id);
    await _prefs?.setString(_modeKey, _modeName(mode));
    await _prefs?.setString(p.isDark ? _lastDarkKey : _lastLightKey, id);
  }

  /// The header's sun/moon button: flip modes, restoring the palette last used
  /// on the other side.
  ///
  /// [current] is what is actually on screen. In system mode the stored palette
  /// may be the opposite brightness, so flipping from it would appear to do
  /// nothing and need a second tap.
  Future<void> toggleMode({Brightness? platform}) async {
    final shown = resolvePalette(
      state,
      platform ?? WidgetsBinding.instance.platformDispatcher.platformBrightness,
    );
    final goingDark = !shown.isDark;
    final remembered =
        _prefs?.getString(goingDark ? _lastDarkKey : _lastLightKey);
    final fallback =
        goingDark ? AppPalette.emerald.id : AppPalette.emeraldLight.id;
    await setPalette(remembered ?? fallback);
  }

  Future<void> setMode(ThemeMode mode) async {
    state = state.copyWith(mode: mode);
    await _prefs?.setString(_modeKey, _modeName(mode));
  }
}

final themeControllerProvider =
    StateNotifierProvider<ThemeController, ThemeSettings>(
  (ref) => ThemeController(),
);

/// The palette actually on screen, given the mode and the device's own setting.
///
/// Takes `platformBrightness` as a parameter rather than reading it from the
/// binding, so the caller can pass a value that rebuilds when the phone
/// switches between light and dark.
AppPalette resolvePalette(ThemeSettings settings, Brightness platform) {
  switch (settings.mode) {
    case ThemeMode.light:
      return settings.lightCounterpart;
    case ThemeMode.dark:
      return settings.darkCounterpart;
    case ThemeMode.system:
      return platform == Brightness.dark
          ? settings.darkCounterpart
          : settings.lightCounterpart;
  }
}

