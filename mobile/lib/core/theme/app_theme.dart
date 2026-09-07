import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_palette.dart';

/// Builds a Material theme from a palette.
///
/// Everything a widget needs comes from `Theme.of(context)` or the
/// [CricColors] extension — no screen reaches for a hard-coded colour, so
/// switching palettes actually restyles the whole app.
class AppTheme {
  const AppTheme._();

  static ThemeData from(AppPalette p) {
    final scheme = ColorScheme(
      brightness: p.brightness,
      primary: p.accent,
      onPrimary: p.accentInk,
      primaryContainer: p.accentSoft,
      onPrimaryContainer: p.accent,
      secondary: p.accent,
      onSecondary: p.accentInk,
      surface: p.surface,
      onSurface: p.ink,
      surfaceContainerHighest: p.surfaceVariant,
      onSurfaceVariant: p.inkMuted,
      error: p.wicket,
      onError: p.isDark ? const Color(0xFF2A0A0E) : Colors.white,
      outline: p.line,
      outlineVariant: p.line,
      shadow: Colors.black.withValues(alpha: p.isDark ? 0.5 : 0.12),
    );

    // Space Grotesk for headings, Manrope for body — the site's pairing.
    final baseText = GoogleFonts.manropeTextTheme(
      p.isDark ? ThemeData.dark().textTheme : ThemeData.light().textTheme,
    ).apply(bodyColor: p.ink, displayColor: p.ink);

    final headingFont = GoogleFonts.spaceGrotesk().fontFamily;

    final textTheme = baseText.copyWith(
      displayLarge: baseText.displayLarge
          ?.copyWith(fontFamily: headingFont, fontWeight: FontWeight.w700),
      displayMedium: baseText.displayMedium
          ?.copyWith(fontFamily: headingFont, fontWeight: FontWeight.w700),
      displaySmall: baseText.displaySmall
          ?.copyWith(fontFamily: headingFont, fontWeight: FontWeight.w700),
      headlineLarge: baseText.headlineLarge
          ?.copyWith(fontFamily: headingFont, fontWeight: FontWeight.w700),
      headlineMedium: baseText.headlineMedium
          ?.copyWith(fontFamily: headingFont, fontWeight: FontWeight.w700),
      headlineSmall: baseText.headlineSmall
          ?.copyWith(fontFamily: headingFont, fontWeight: FontWeight.w700),
      titleLarge: baseText.titleLarge
          ?.copyWith(fontFamily: headingFont, fontWeight: FontWeight.w700),
      titleMedium: baseText.titleMedium?.copyWith(fontWeight: FontWeight.w700),
      titleSmall: baseText.titleSmall?.copyWith(fontWeight: FontWeight.w600),
      bodySmall: baseText.bodySmall?.copyWith(color: p.inkMuted),
      labelSmall: baseText.labelSmall?.copyWith(color: p.inkMuted),
    );

    return ThemeData(
      useMaterial3: true,
      brightness: p.brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: p.background,
      canvasColor: p.background,
      textTheme: textTheme,
      dividerColor: p.line,
      splashFactory: InkSparkle.splashFactory,
      extensions: <ThemeExtension<dynamic>>[CricColors.of(p)],
      appBarTheme: AppBarTheme(
        backgroundColor: p.background,
        foregroundColor: p.ink,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: textTheme.titleLarge?.copyWith(fontSize: 19),
        iconTheme: IconThemeData(color: p.ink),
      ),
      cardTheme: CardThemeData(
        color: p.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        clipBehavior: Clip.antiAlias,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: p.line),
        ),
      ),
      dividerTheme: DividerThemeData(color: p.line, space: 1, thickness: 1),
      listTileTheme: ListTileThemeData(
        iconColor: p.inkMuted,
        textColor: p.ink,
        titleTextStyle: textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        subtitleTextStyle: textTheme.bodySmall,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: p.inputFill,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        hintStyle: textTheme.bodyMedium?.copyWith(color: p.faint),
        labelStyle: textTheme.bodyMedium?.copyWith(color: p.inkMuted),
        floatingLabelStyle: textTheme.bodySmall?.copyWith(color: p.accent),
        border: _border(p.line),
        enabledBorder: _border(p.line),
        focusedBorder: _border(p.accent, width: 1.6),
        errorBorder: _border(p.wicket),
        focusedErrorBorder: _border(p.wicket, width: 1.6),
        prefixIconColor: p.inkMuted,
        suffixIconColor: p.inkMuted,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: p.accent,
          foregroundColor: p.accentInk,
          disabledBackgroundColor: p.accent.withValues(alpha: 0.35),
          disabledForegroundColor: p.accentInk.withValues(alpha: 0.7),
          elevation: 0,
          minimumSize: const Size(0, 48),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: textTheme.titleSmall?.copyWith(fontSize: 15),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: p.ink,
          minimumSize: const Size(0, 48),
          side: BorderSide(color: p.line),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: textTheme.titleSmall?.copyWith(fontSize: 15),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: p.accent,
          textStyle: textTheme.titleSmall?.copyWith(fontSize: 14),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: p.accentSoft,
          foregroundColor: p.accent,
          elevation: 0,
          minimumSize: const Size(0, 44),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: p.accent,
        foregroundColor: p.accentInk,
        elevation: 2,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: p.surfaceVariant,
        selectedColor: p.accentSoft,
        side: BorderSide(color: p.line),
        labelStyle: textTheme.labelLarge?.copyWith(color: p.ink),
        secondaryLabelStyle: textTheme.labelLarge?.copyWith(color: p.accent),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: p.surface,
        surfaceTintColor: Colors.transparent,
        indicatorColor: p.accentSoft,
        elevation: 0,
        height: 66,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => textTheme.labelSmall?.copyWith(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: states.contains(WidgetState.selected) ? p.accent : p.faint,
          ),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            size: 23,
            color: states.contains(WidgetState.selected) ? p.accent : p.faint,
          ),
        ),
      ),
      tabBarTheme: TabBarThemeData(
        labelColor: p.accent,
        unselectedLabelColor: p.inkMuted,
        indicatorColor: p.accent,
        indicatorSize: TabBarIndicatorSize.label,
        dividerColor: p.line,
        labelStyle: textTheme.titleSmall,
        unselectedLabelStyle: textTheme.titleSmall
            ?.copyWith(fontWeight: FontWeight.w500),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: p.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: BorderSide(color: p.line),
        ),
        titleTextStyle: textTheme.titleLarge?.copyWith(fontSize: 18),
        contentTextStyle: textTheme.bodyMedium,
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: p.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        showDragHandle: true,
        dragHandleColor: p.faint,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: p.isDark ? p.surfaceVariant : const Color(0xFF1F2422),
        contentTextStyle: textTheme.bodyMedium?.copyWith(
          color: p.isDark ? p.ink : Colors.white,
        ),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        elevation: 2,
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? p.accent : p.faint,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected)
              ? p.accentSoft
              : p.surfaceVariant,
        ),
        trackOutlineColor: WidgetStateProperty.all(p.line),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? p.accent : Colors.transparent,
        ),
        checkColor: WidgetStateProperty.all(p.accentInk),
        side: BorderSide(color: p.faint, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
      ),
      radioTheme: RadioThemeData(
        fillColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? p.accent : p.faint,
        ),
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: p.accent,
        inactiveTrackColor: p.surfaceVariant,
        thumbColor: p.accent,
        overlayColor: p.accentSoft,
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: p.accent,
        linearTrackColor: p.surfaceVariant,
        circularTrackColor: p.surfaceVariant,
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: p.isDark ? p.surfaceVariant : const Color(0xFF1F2422),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: p.line),
        ),
        textStyle: textTheme.bodySmall?.copyWith(
          color: p.isDark ? p.ink : Colors.white,
        ),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: p.surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: p.line),
        ),
      ),
      dropdownMenuTheme: DropdownMenuThemeData(
        menuStyle: MenuStyle(
          backgroundColor: WidgetStateProperty.all(p.surface),
          surfaceTintColor: WidgetStateProperty.all(Colors.transparent),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: p.line),
            ),
          ),
        ),
      ),
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: ButtonStyle(
          backgroundColor: WidgetStateProperty.resolveWith(
            (s) => s.contains(WidgetState.selected)
                ? p.accentSoft
                : Colors.transparent,
          ),
          foregroundColor: WidgetStateProperty.resolveWith(
            (s) => s.contains(WidgetState.selected) ? p.accent : p.inkMuted,
          ),
          side: WidgetStateProperty.all(BorderSide(color: p.line)),
          textStyle: WidgetStateProperty.all(textTheme.labelLarge),
        ),
      ),
    );
  }

  static OutlineInputBorder _border(Color color, {double width = 1}) =>
      OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: color, width: width),
      );
}

/// Cricket-specific colours that Material's ColorScheme has no slot for.
@immutable
class CricColors extends ThemeExtension<CricColors> {
  final Color wicket;
  final Color wicketSoft;
  final Color four;
  final Color fourSoft;
  final Color six;
  final Color sixSoft;
  final Color amber;
  final Color amberSoft;
  final Color accentSoft;
  final Color surfaceVariant;
  final Color muted;
  final Color faint;
  final Color line;

  const CricColors({
    required this.wicket,
    required this.wicketSoft,
    required this.four,
    required this.fourSoft,
    required this.six,
    required this.sixSoft,
    required this.amber,
    required this.amberSoft,
    required this.accentSoft,
    required this.surfaceVariant,
    required this.muted,
    required this.faint,
    required this.line,
  });

  factory CricColors.of(AppPalette p) => CricColors(
        wicket: p.wicket,
        wicketSoft: p.wicketSoft,
        four: p.four,
        fourSoft: p.fourSoft,
        six: p.six,
        sixSoft: p.sixSoft,
        amber: p.amber,
        amberSoft: p.amberSoft,
        accentSoft: p.accentSoft,
        surfaceVariant: p.surfaceVariant,
        muted: p.inkMuted,
        faint: p.faint,
        line: p.line,
      );

  @override
  CricColors copyWith({
    Color? wicket,
    Color? wicketSoft,
    Color? four,
    Color? fourSoft,
    Color? six,
    Color? sixSoft,
    Color? amber,
    Color? amberSoft,
    Color? accentSoft,
    Color? surfaceVariant,
    Color? muted,
    Color? faint,
    Color? line,
  }) =>
      CricColors(
        wicket: wicket ?? this.wicket,
        wicketSoft: wicketSoft ?? this.wicketSoft,
        four: four ?? this.four,
        fourSoft: fourSoft ?? this.fourSoft,
        six: six ?? this.six,
        sixSoft: sixSoft ?? this.sixSoft,
        amber: amber ?? this.amber,
        amberSoft: amberSoft ?? this.amberSoft,
        accentSoft: accentSoft ?? this.accentSoft,
        surfaceVariant: surfaceVariant ?? this.surfaceVariant,
        muted: muted ?? this.muted,
        faint: faint ?? this.faint,
        line: line ?? this.line,
      );

  @override
  CricColors lerp(ThemeExtension<CricColors>? other, double t) {
    if (other is! CricColors) return this;
    return CricColors(
      wicket: Color.lerp(wicket, other.wicket, t)!,
      wicketSoft: Color.lerp(wicketSoft, other.wicketSoft, t)!,
      four: Color.lerp(four, other.four, t)!,
      fourSoft: Color.lerp(fourSoft, other.fourSoft, t)!,
      six: Color.lerp(six, other.six, t)!,
      sixSoft: Color.lerp(sixSoft, other.sixSoft, t)!,
      amber: Color.lerp(amber, other.amber, t)!,
      amberSoft: Color.lerp(amberSoft, other.amberSoft, t)!,
      accentSoft: Color.lerp(accentSoft, other.accentSoft, t)!,
      surfaceVariant: Color.lerp(surfaceVariant, other.surfaceVariant, t)!,
      muted: Color.lerp(muted, other.muted, t)!,
      faint: Color.lerp(faint, other.faint, t)!,
      line: Color.lerp(line, other.line, t)!,
    );
  }
}

/// `context.cric.wicket` instead of digging through theme extensions.
extension CricColorsX on BuildContext {
  CricColors get cric =>
      Theme.of(this).extension<CricColors>() ?? CricColors.of(AppPalette.emerald);

  ColorScheme get scheme => Theme.of(this).colorScheme;
  TextTheme get texts => Theme.of(this).textTheme;
}
