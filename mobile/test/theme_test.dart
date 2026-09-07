import 'package:cricnetra/core/theme/app_palette.dart';
import 'package:cricnetra/core/theme/theme_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('following the device theme', () {
    test('a fresh install follows the phone', () {
      const fresh = ThemeSettings();
      expect(fresh.followsSystem, isTrue);

      expect(
        resolvePalette(fresh, Brightness.dark).isDark,
        isTrue,
        reason: 'a dark phone should get a dark app',
      );
      expect(
        resolvePalette(fresh, Brightness.light).isDark,
        isFalse,
        reason: 'a light phone should get a light app',
      );
    });

    test('a chosen dark palette is kept when the phone goes dark', () {
      const settings = ThemeSettings(paletteId: 'ocean');
      expect(resolvePalette(settings, Brightness.dark).id, 'ocean');
      // On a light phone the app needs a light palette, so it falls back.
      expect(resolvePalette(settings, Brightness.light).isDark, isFalse);
    });

    test('a chosen light palette is kept when the phone goes light', () {
      const settings = ThemeSettings(paletteId: 'blossom');
      expect(resolvePalette(settings, Brightness.light).id, 'blossom');
      expect(resolvePalette(settings, Brightness.dark).isDark, isTrue);
    });

    test('pinning a mode ignores the phone', () {
      const pinnedDark =
          ThemeSettings(paletteId: 'carbon', mode: ThemeMode.dark);
      expect(resolvePalette(pinnedDark, Brightness.light).id, 'carbon');

      const pinnedLight = ThemeSettings(paletteId: 'sand', mode: ThemeMode.light);
      expect(resolvePalette(pinnedLight, Brightness.dark).id, 'sand');
    });
  });

  group('palettes', () {
    test('every palette is reachable by id and keeps its brightness', () {
      for (final p in AppPalette.all) {
        expect(AppPalette.byId(p.id).id, p.id);
      }
      expect(AppPalette.darkPalettes.every((p) => p.isDark), isTrue);
      expect(AppPalette.lightPalettes.every((p) => !p.isDark), isTrue);
    });

    test('an unknown id falls back rather than throwing', () {
      expect(AppPalette.byId('does-not-exist').id, 'emerald');
    });

    test('there are twelve looks, matching the website', () {
      expect(AppPalette.all.length, 12);
    });
  });
}
