import 'package:flutter/material.dart';

/// A colour scheme, ported from the website's CSS custom properties.
///
/// The web app ships twelve palettes behind Settings → Theme. The same set is
/// reproduced here so a person's chosen look carries across surfaces.
class AppPalette {
  final String id;
  final String name;
  final Brightness brightness;

  final Color accent;

  /// Text drawn ON the accent (a filled button's label).
  final Color accentInk;
  final Color background;
  final Color surface;
  final Color surfaceVariant;
  final Color inputFill;
  final Color line;
  final Color ink;
  final Color inkMuted;
  final Color faint;

  // Semantic colours for cricket events.
  final Color wicket;
  final Color four;
  final Color six;
  final Color amber;

  const AppPalette({
    required this.id,
    required this.name,
    required this.brightness,
    required this.accent,
    required this.accentInk,
    required this.background,
    required this.surface,
    required this.surfaceVariant,
    required this.inputFill,
    required this.line,
    required this.ink,
    required this.inkMuted,
    required this.faint,
    this.wicket = const Color(0xFFFF5D6C),
    this.four = const Color(0xFF4F91FF),
    this.six = const Color(0xFFB794FF),
    this.amber = const Color(0xFFF5A623),
  });

  bool get isDark => brightness == Brightness.dark;

  Color get accentSoft => accent.withValues(alpha: 0.13);
  Color get accentLine => accent.withValues(alpha: 0.26);
  Color get wicketSoft => wicket.withValues(alpha: 0.14);
  Color get fourSoft => four.withValues(alpha: 0.14);
  Color get sixSoft => six.withValues(alpha: 0.14);
  Color get amberSoft => amber.withValues(alpha: 0.14);

  static const gold = Color(0xFFF5B301);
  static const silver = Color(0xFF9AA7B1);
  static const bronze = Color(0xFFCD8B50);

  /// Medal colour for a leaderboard rank (1-based); null past third place.
  static Color? medal(int rank) => switch (rank) {
        1 => gold,
        2 => silver,
        3 => bronze,
        _ => null,
      };

  // ------------------------------------------------------------ dark set

  static const emerald = AppPalette(
    id: 'emerald',
    name: 'Emerald',
    brightness: Brightness.dark,
    accent: Color(0xFF2FE08A),
    accentInk: Color(0xFF06231A),
    background: Color(0xFF080B0A),
    surface: Color(0xFF101714),
    surfaceVariant: Color(0xFF0C1210),
    inputFill: Color(0xFF0C1210),
    line: Color(0x1FFFFFFF),
    ink: Color(0xFFE8EFEB),
    inkMuted: Color(0xFF9BB0A6),
    faint: Color(0xFF56685F),
  );

  static const ocean = AppPalette(
    id: 'ocean',
    name: 'Midnight Ocean',
    brightness: Brightness.dark,
    accent: Color(0xFF34C8FF),
    accentInk: Color(0xFF04202E),
    background: Color(0xFF060B12),
    surface: Color(0xFF0E1A24),
    surfaceVariant: Color(0xFF0A141C),
    inputFill: Color(0xFF0A141C),
    line: Color(0x2478BEFF),
    ink: Color(0xFFE6F0F7),
    inkMuted: Color(0xFF98B3C6),
    faint: Color(0xFF4E6678),
  );

  static const carbon = AppPalette(
    id: 'carbon',
    name: 'Carbon',
    brightness: Brightness.dark,
    accent: Color(0xFFBEF264),
    accentInk: Color(0xFF1A2606),
    background: Color(0xFF0A0B0C),
    surface: Color(0xFF16181B),
    surfaceVariant: Color(0xFF101214),
    inputFill: Color(0xFF101214),
    line: Color(0x21FFFFFF),
    ink: Color(0xFFECEEF0),
    inkMuted: Color(0xFFA4ACB2),
    faint: Color(0xFF596068),
  );

  // ----------------------------------------------------------- light set

  static const _lightWicket = Color(0xFFE5484D);
  static const _lightFour = Color(0xFF2F6FED);
  static const _lightSix = Color(0xFF7C5CFF);
  static const _lightAmber = Color(0xFFB4710A);

  static const emeraldLight = AppPalette(
    id: 'emerald_light',
    name: 'Emerald',
    brightness: Brightness.light,
    accent: Color(0xFF0C9B54),
    accentInk: Colors.white,
    background: Color(0xFFEEF4F0),
    surface: Colors.white,
    surfaceVariant: Color(0xFFF4F8F5),
    inputFill: Color(0xFFF4F8F5),
    line: Color(0x1A10281E),
    ink: Color(0xFF0F1D16),
    inkMuted: Color(0xFF46564E),
    faint: Color(0xFF94A39B),
    wicket: _lightWicket,
    four: _lightFour,
    six: _lightSix,
    amber: _lightAmber,
  );

  static const mint = AppPalette(
    id: 'mint',
    name: 'Mint',
    brightness: Brightness.light,
    accent: Color(0xFF0E9F6E),
    accentInk: Colors.white,
    background: Color(0xFFEEF7F2),
    surface: Colors.white,
    surfaceVariant: Color(0xFFF1F8F4),
    inputFill: Color(0xFFF1F8F4),
    line: Color(0x1A0C503A),
    ink: Color(0xFF10241C),
    inkMuted: Color(0xFF46605A),
    faint: Color(0xFF9CB4AC),
    wicket: _lightWicket,
    four: _lightFour,
    six: _lightSix,
    amber: _lightAmber,
  );

  static const blossom = AppPalette(
    id: 'blossom',
    name: 'Blossom',
    brightness: Brightness.light,
    accent: Color(0xFFDB2777),
    accentInk: Colors.white,
    background: Color(0xFFFDF0F6),
    surface: Colors.white,
    surfaceVariant: Color(0xFFFCF1F7),
    inputFill: Color(0xFFFCF1F7),
    line: Color(0x17781E46),
    ink: Color(0xFF2A1620),
    inkMuted: Color(0xFF6B4C5A),
    faint: Color(0xFFBDA3AE),
    wicket: _lightWicket,
    four: _lightFour,
    six: _lightSix,
    amber: _lightAmber,
  );

  static const rose = AppPalette(
    id: 'rose',
    name: 'Rose',
    brightness: Brightness.light,
    accent: Color(0xFFE11D48),
    accentInk: Colors.white,
    background: Color(0xFFFDF1F3),
    surface: Colors.white,
    surfaceVariant: Color(0xFFFCF2F4),
    inputFill: Color(0xFFFCF2F4),
    line: Color(0x179F1239),
    ink: Color(0xFF2B151A),
    inkMuted: Color(0xFF6B4A52),
    faint: Color(0xFFBBA1A7),
    wicket: _lightWicket,
    four: _lightFour,
    six: _lightSix,
    amber: _lightAmber,
  );

  static const slate = AppPalette(
    id: 'slate',
    name: 'Slate',
    brightness: Brightness.light,
    accent: Color(0xFF475569),
    accentInk: Colors.white,
    background: Color(0xFFF1F3F5),
    surface: Colors.white,
    surfaceVariant: Color(0xFFF6F8FA),
    inputFill: Color(0xFFF6F8FA),
    line: Color(0x1A1E293B),
    ink: Color(0xFF0F172A),
    inkMuted: Color(0xFF475569),
    faint: Color(0xFF94A3B8),
    wicket: _lightWicket,
    four: _lightFour,
    six: _lightSix,
    amber: _lightAmber,
  );

  static const sand = AppPalette(
    id: 'sand',
    name: 'Sand',
    brightness: Brightness.light,
    accent: Color(0xFFB45309),
    accentInk: Colors.white,
    background: Color(0xFFF7F2E9),
    surface: Colors.white,
    surfaceVariant: Color(0xFFFAF6EF),
    inputFill: Color(0xFFFAF6EF),
    line: Color(0x1A78350F),
    ink: Color(0xFF261B10),
    inkMuted: Color(0xFF61503C),
    faint: Color(0xFFB3A28C),
    wicket: _lightWicket,
    four: _lightFour,
    six: _lightSix,
    amber: _lightAmber,
  );

  static const lavender = AppPalette(
    id: 'lavender',
    name: 'Lavender',
    brightness: Brightness.light,
    accent: Color(0xFF7C3AED),
    accentInk: Colors.white,
    background: Color(0xFFF4F1FD),
    surface: Colors.white,
    surfaceVariant: Color(0xFFF8F5FE),
    inputFill: Color(0xFFF8F5FE),
    line: Color(0x175B21B6),
    ink: Color(0xFF1E1630),
    inkMuted: Color(0xFF544A6B),
    faint: Color(0xFFA79EBC),
    wicket: _lightWicket,
    four: _lightFour,
    six: _lightSix,
    amber: _lightAmber,
  );

  static const sky = AppPalette(
    id: 'sky',
    name: 'Sky',
    brightness: Brightness.light,
    accent: Color(0xFF0284C7),
    accentInk: Colors.white,
    background: Color(0xFFEEF5FB),
    surface: Colors.white,
    surfaceVariant: Color(0xFFF3F8FC),
    inputFill: Color(0xFFF3F8FC),
    line: Color(0x1A075985),
    ink: Color(0xFF0C1E2A),
    inkMuted: Color(0xFF445A69),
    faint: Color(0xFF93A8B5),
    wicket: _lightWicket,
    four: _lightFour,
    six: _lightSix,
    amber: _lightAmber,
  );

  static const sunset = AppPalette(
    id: 'sunset',
    name: 'Sunset',
    brightness: Brightness.light,
    accent: Color(0xFFEA580C),
    accentInk: Colors.white,
    background: Color(0xFFFDF3EC),
    surface: Colors.white,
    surfaceVariant: Color(0xFFFDF6F0),
    inputFill: Color(0xFFFDF6F0),
    line: Color(0x1A9A3412),
    ink: Color(0xFF2A1810),
    inkMuted: Color(0xFF6A503F),
    faint: Color(0xFFBBA391),
    wicket: _lightWicket,
    four: _lightFour,
    six: _lightSix,
    amber: _lightAmber,
  );

  static const darkPalettes = <AppPalette>[emerald, ocean, carbon];

  static const lightPalettes = <AppPalette>[
    mint,
    blossom,
    emeraldLight,
    rose,
    slate,
    sand,
    lavender,
    sky,
    sunset,
  ];

  static const all = <AppPalette>[...darkPalettes, ...lightPalettes];

  static AppPalette byId(String id) {
    for (final p in all) {
      if (p.id == id) return p;
    }
    return emerald;
  }
}
